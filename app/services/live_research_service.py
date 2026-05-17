import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import requests

from app.core import config


@dataclass(frozen=True)
class ResearchQuery:
    query: str
    locale: str = "ko-KR"
    freshness_required: bool = False
    topic: str = "food"
    max_sources: int = 5


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


_FRESHNESS_PATTERN = re.compile(
    r"(최신|최근|요즘|요새|유행|트렌드|SNS|인스타|틱톡|릴스|올해|이번\s*시즌|제철)",
    re.IGNORECASE,
)
_LIVE_RESEARCH_INTENTS = {
    "RECIPE_RECOMMENDATION",
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "DIET_OR_ALLERGY",
}


class LiveResearchService:
    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        source_policy: SourcePolicy | None = None,
        citation_builder: CitationBuilder | None = None,
    ) -> None:
        self.search_provider = search_provider or DisabledSearchProvider()
        self.source_policy = source_policy or SourcePolicy()
        self.citation_builder = citation_builder or CitationBuilder()
        self._cache: dict[str, CacheEntry] = {}

    def should_research(self, intent_type: str, message: str) -> bool:
        return (
            intent_type in _LIVE_RESEARCH_INTENTS
            and bool(_FRESHNESS_PATTERN.search(message))
        )

    def build_query(
        self,
        message: str,
        intent_type: str,
        locale: str = "ko-KR",
        max_sources: int = 5,
    ) -> ResearchQuery:
        return ResearchQuery(
            query=message.strip(),
            locale=locale,
            freshness_required=self.should_research(intent_type, message),
            topic=_topic_for_intent(intent_type),
            max_sources=max_sources,
        )

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


live_research_service = LiveResearchService(search_provider=get_search_provider())


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


def _topic_for_intent(intent_type: str) -> str:
    if intent_type == "DIET_OR_ALLERGY":
        return "diet"
    if intent_type in {"COOKING_TIP", "INGREDIENT_SUBSTITUTION"}:
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
