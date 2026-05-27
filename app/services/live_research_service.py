import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.intent.intent_models import PrimaryTask
from app.core import config


@dataclass(frozen=True)
class ResearchQuery:
    query: str
    locale: str = "ko-KR"
    freshness_required: bool = False
    topic: str = "food"
    max_sources: int = 5


class LiveResearchDecision(BaseModel):
    should_research: bool = False
    query: str | None = None
    freshness_required: bool = False
    topic: str = "food"
    reason: str | None = None


@dataclass(frozen=True)
class SearchCandidate:
    title: str
    url: str
    publisher: str | None = None
    published_at: str | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class ResearchEvidence:
    title: str
    url: str
    publisher: str | None
    published_at: str | None
    fetched_at: datetime
    summary: str
    confidence: float


@dataclass(frozen=True)
class LiveResearchResult:
    answer_context: str | None
    evidence: list[ResearchEvidence]
    used_at: datetime
    cache_key: str | None = None
    from_cache: bool = False

    @property
    def used_live_research(self) -> bool:
        return bool(self.evidence)


@dataclass
class CacheEntry:
    result: LiveResearchResult
    expires_at: datetime


class SearchProvider(Protocol):
    def search(self, query: ResearchQuery) -> list[SearchCandidate]:
        pass


class DisabledSearchProvider:
    def search(self, query: ResearchQuery) -> list[SearchCandidate]:
        return []


class BraveSearchProvider:
    def __init__(
        self,
        api_key: str,
        endpoint: str = config.BRAVE_SEARCH_ENDPOINT,
        timeout_seconds: float = config.LIVE_SEARCH_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def search(self, query: ResearchQuery) -> list[SearchCandidate]:
        response = requests.get(
            self.endpoint,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            params=_brave_params(query),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return _parse_brave_results(payload)


class SourcePolicy:
    _blocked_hosts = {
        "pinterest.com",
        "www.pinterest.com",
    }
    _low_quality_patterns = re.compile(
        r"(광고|복붙|자동\s*생성|무단\s*복제|스팸)",
        re.IGNORECASE,
    )

    def filter_candidates(
        self,
        candidates: list[SearchCandidate],
        max_sources: int,
    ) -> list[SearchCandidate]:
        accepted = []
        seen_urls = set()
        for candidate in candidates:
            if len(accepted) >= max_sources:
                break
            if candidate.url in seen_urls:
                continue
            if not self.is_allowed(candidate):
                continue
            accepted.append(candidate)
            seen_urls.add(candidate.url)
        return accepted

    def is_allowed(self, candidate: SearchCandidate) -> bool:
        parsed = urlparse(candidate.url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.hostname in self._blocked_hosts:
            return False
        text = " ".join(
            part
            for part in [candidate.title, candidate.publisher, candidate.snippet]
            if part
        )
        return not self._low_quality_patterns.search(text)


class CitationBuilder:
    def build_context(self, evidence: list[ResearchEvidence]) -> str | None:
        if not evidence:
            return None
        lines = ["Live research evidence:"]
        for item in evidence:
            published = item.published_at or "unknown date"
            publisher = item.publisher or "unknown publisher"
            lines.append(
                f"- Source: {item.title} ({publisher}, {published})\n"
                f"  URL: {item.url}\n"
                f"  Summary: {item.summary}"
            )
        return "\n".join(lines)


_LIVE_RESEARCH_TASKS = {
    PrimaryTask.RECIPE_FIND,
    PrimaryTask.COOKING_QA,
}


class LiveResearchService:
    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        source_policy: SourcePolicy | None = None,
        citation_builder: CitationBuilder | None = None,
        decision_agent: Agent | None = None,
    ) -> None:
        self.search_provider = search_provider or DisabledSearchProvider()
        self.source_policy = source_policy or SourcePolicy()
        self.citation_builder = citation_builder or CitationBuilder()
        self.decision_agent = decision_agent or _build_live_research_decision_agent()
        self._cache: dict[str, CacheEntry] = {}

    def should_research(self, primary_task: PrimaryTask | str, message: str) -> bool:
        return self.decide(primary_task, message).should_research

    def build_query(
        self,
        message: str,
        primary_task: PrimaryTask | str,
        locale: str = "ko-KR",
        max_sources: int = 5,
    ) -> ResearchQuery:
        decision = self.decide(primary_task, message)
        return ResearchQuery(
            query=(decision.query or message).strip(),
            locale=locale,
            freshness_required=decision.freshness_required,
            topic=decision.topic or _topic_for_task(_coerce_primary_task(primary_task)),
            max_sources=max_sources,
        )

    def decide(
        self,
        primary_task: PrimaryTask | str,
        message: str,
    ) -> LiveResearchDecision:
        task = _coerce_primary_task(primary_task)
        if task not in _LIVE_RESEARCH_TASKS:
            return LiveResearchDecision(
                should_research=False,
                query=None,
                freshness_required=False,
                topic=_topic_for_task(task),
                reason="task is not eligible for live research",
            )
        result = self.decision_agent.run_sync(
            f"[Primary task]\n{task.value}\n\n[User message]\n{message.strip()}"
        )
        output = result.output
        if output.should_research and not output.query:
            return output.model_copy(update={"query": message.strip()})
        return output

    def research(self, query: ResearchQuery) -> LiveResearchResult:
        now = datetime.now(UTC)
        cache_key = _cache_key(query, now)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return LiveResearchResult(
                answer_context=cached.result.answer_context,
                evidence=cached.result.evidence,
                used_at=now,
                cache_key=cache_key,
                from_cache=True,
            )

        candidates = self.search_provider.search(query)
        filtered = self.source_policy.filter_candidates(
            candidates,
            max_sources=min(query.max_sources, 5),
        )
        evidence = [
            _candidate_to_evidence(candidate, now)
            for candidate in filtered[:3]
        ]
        answer_context = self.citation_builder.build_context(evidence)
        result = LiveResearchResult(
            answer_context=answer_context,
            evidence=evidence,
            used_at=now,
            cache_key=cache_key,
        )
        self._cache[cache_key] = CacheEntry(
            result=result,
            expires_at=now + _ttl_for_query(query),
        )
        return result


def get_search_provider() -> SearchProvider:
    provider = config.LIVE_SEARCH_PROVIDER.strip().lower()
    if provider in {"", "disabled", "none", "off"}:
        return DisabledSearchProvider()
    if provider == "brave":
        if not config.BRAVE_SEARCH_API_KEY:
            return DisabledSearchProvider()
        return BraveSearchProvider(
            api_key=config.BRAVE_SEARCH_API_KEY,
            endpoint=config.BRAVE_SEARCH_ENDPOINT,
            timeout_seconds=config.LIVE_SEARCH_TIMEOUT_SECONDS,
        )
    return DisabledSearchProvider()


def _build_live_research_decision_agent() -> Agent:
    model = OpenAIChatModel(
        config.MODEL_NAME,
        provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
    )
    return Agent(
        model,
        output_type=LiveResearchDecision,
        system_prompt=_LIVE_RESEARCH_DECISION_PROMPT,
    )


def _brave_params(query: ResearchQuery) -> dict[str, Any]:
    params: dict[str, Any] = {
        "q": query.query,
        "count": min(max(query.max_sources, 1), 10),
        "safesearch": "moderate",
    }
    if query.locale.startswith("ko"):
        params["country"] = "KR"
        params["search_lang"] = "ko"
    if query.freshness_required:
        params["freshness"] = "pd"
    return params


def _parse_brave_results(payload: dict[str, Any]) -> list[SearchCandidate]:
    web_results = payload.get("web", {}).get("results", [])
    if not isinstance(web_results, list):
        return []
    return [
        SearchCandidate(
            title=str(item.get("title") or "").strip(),
            url=str(item.get("url") or "").strip(),
            publisher=_brave_publisher(item),
            published_at=_brave_published_at(item),
            snippet=_brave_snippet(item),
        )
        for item in web_results
        if isinstance(item, dict) and item.get("title") and item.get("url")
    ]


def _brave_publisher(item: dict[str, Any]) -> str | None:
    profile = item.get("profile")
    if isinstance(profile, dict):
        name = profile.get("name")
        if name:
            return str(name)
    meta_url = item.get("meta_url")
    if isinstance(meta_url, dict) and meta_url.get("hostname"):
        return str(meta_url["hostname"])
    hostname = urlparse(str(item.get("url") or "")).hostname
    return hostname


def _brave_published_at(item: dict[str, Any]) -> str | None:
    age = item.get("age")
    if not age:
        return None
    try:
        return parsedate_to_datetime(str(age)).date().isoformat()
    except (TypeError, ValueError):
        return str(age)


def _brave_snippet(item: dict[str, Any]) -> str | None:
    snippets = item.get("extra_snippets")
    if isinstance(snippets, list) and snippets:
        text = " ".join(str(snippet) for snippet in snippets[:2] if snippet)
        if text:
            return text
    description = item.get("description")
    return str(description) if description else None


def _candidate_to_evidence(
    candidate: SearchCandidate,
    fetched_at: datetime,
) -> ResearchEvidence:
    return ResearchEvidence(
        title=candidate.title,
        url=candidate.url,
        publisher=candidate.publisher,
        published_at=candidate.published_at,
        fetched_at=fetched_at,
        summary=candidate.snippet or candidate.title,
        confidence=_candidate_confidence(candidate),
    )


def _candidate_confidence(candidate: SearchCandidate) -> float:
    score = 0.65
    if candidate.publisher:
        score += 0.1
    if candidate.published_at:
        score += 0.1
    if candidate.snippet:
        score += 0.05
    return min(round(score, 2), 0.9)


def _coerce_primary_task(value: PrimaryTask | str) -> PrimaryTask:
    if isinstance(value, PrimaryTask):
        return value
    try:
        return PrimaryTask(value)
    except ValueError:
        return PrimaryTask.OFF_TOPIC


def _topic_for_task(primary_task: PrimaryTask) -> str:
    if primary_task == PrimaryTask.COOKING_QA:
        return "cooking_info"
    return "food_trend"


def _cache_key(query: ResearchQuery, now: datetime) -> str:
    normalized = re.sub(r"\s+", " ", query.query.strip().lower())
    bucket = _date_bucket(query, now)
    return f"live_research:{query.locale}:{normalized}:{bucket}"


def _date_bucket(query: ResearchQuery, now: datetime) -> str:
    if query.freshness_required or query.topic == "food_trend":
        return now.strftime("%Y-%m-%d")
    if query.topic == "seasonal":
        year, week, _ = now.isocalendar()
        return f"{year}-W{week:02d}"
    return now.strftime("%Y-%m")


def _ttl_for_query(query: ResearchQuery) -> timedelta:
    if query.freshness_required or query.topic == "food_trend":
        return timedelta(days=1)
    if query.topic == "seasonal":
        return timedelta(days=7)
    return timedelta(days=30)


_LIVE_RESEARCH_DECISION_PROMPT = """
You decide whether a cooking assistant needs external live web research.
Return structured output only.

Use live research only when the user needs current, recent, seasonal, trend, or
external-evidence information that the local recipe database may not contain.
Do not use live research for ordinary recipe recommendations or general cooking
questions that can be answered without current web evidence.

If should_research is true:
- query must be a concise web search query in Korean.
- remove personal, medical, allergy, identity, and account details from query.
- keep only the food topic and freshness need.
- freshness_required should be true for current or trend-sensitive requests.
- topic should be food_trend, cooking_info, or seasonal.

If the message contains sensitive personal or health details, never include
those details in query. If removing them leaves no useful current-search topic,
set should_research=false.

Examples:
- "요즘 유행하는 김밥 뭐야?"
  => should_research=true, query="요즘 유행하는 김밥"
- "요즘 당뇨 때문에 저탄수 레시피 뭐가 좋아?"
  => should_research=true, query="요즘 저탄수 레시피"
- "요즘 새우 알레르기 있는데 유행 레시피 추천해줘"
  => should_research=true, query="요즘 유행 레시피"
- "김치랑 두부 있어"
  => should_research=false
""".strip()


live_research_service = LiveResearchService(search_provider=get_search_provider())
