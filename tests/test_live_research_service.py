from app.services.live_research_service import (
    BraveSearchProvider,
    DisabledSearchProvider,
    LiveResearchService,
    ResearchQuery,
    SearchCandidate,
    SourcePolicy,
    get_search_provider,
)


class FakeSearchProvider:
    def __init__(self):
        self.calls = 0

    def search(self, query: ResearchQuery) -> list[SearchCandidate]:
        self.calls += 1
        return [
            SearchCandidate(
                title="요즘 인기 있는 김밥 트렌드",
                url="https://example.com/kimbap-trend",
                publisher="Example Food",
                published_at="2026-05-01",
                snippet="김밥 변형 레시피가 SNS에서 자주 언급됩니다.",
            )
        ]


def test_should_research_for_fresh_food_intent():
    service = LiveResearchService()

    assert service.should_research("RECIPE_RECOMMENDATION", "요즘 유행하는 요리 뭐야?")
    assert not service.should_research("RECIPE_RECOMMENDATION", "김치랑 두부 있어")
    assert not service.should_research("OFF_TOPIC", "요즘 주식 알려줘")


def test_source_policy_filters_invalid_and_low_quality_candidates():
    candidates = [
        SearchCandidate(title="valid", url="https://example.com/a"),
        SearchCandidate(title="duplicate", url="https://example.com/a"),
        SearchCandidate(title="ftp", url="ftp://example.com/b"),
        SearchCandidate(title="광고 복붙 페이지", url="https://example.com/c"),
        SearchCandidate(title="pinterest", url="https://www.pinterest.com/pin/1"),
    ]

    result = SourcePolicy().filter_candidates(candidates, max_sources=5)

    assert result == [candidates[0]]


def test_research_builds_context_and_uses_cache():
    provider = FakeSearchProvider()
    service = LiveResearchService(search_provider=provider)
    query = ResearchQuery(
        query="요즘 유행하는 김밥",
        freshness_required=True,
        topic="food_trend",
    )

    first = service.research(query)
    second = service.research(query)

    assert provider.calls == 1
    assert first.used_live_research is True
    assert second.from_cache is True
    assert first.answer_context is not None
    assert "Live research evidence" in first.answer_context
    assert first.evidence[0].confidence == 0.9


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.raised = False

    def raise_for_status(self):
        self.raised = True

    def json(self):
        return self.payload


def test_brave_provider_maps_web_results(monkeypatch):
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return FakeResponse(
            {
                "web": {
                    "results": [
                        {
                            "title": "요즘 인기 김밥",
                            "url": "https://example.com/kimbap",
                            "description": "SNS에서 접는 김밥이 인기입니다.",
                            "profile": {"name": "Example Food"},
                            "age": "Sat, 16 May 2026 00:00:00 GMT",
                            "extra_snippets": ["김밥 트렌드", "간편식 인기"],
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("app.services.live_research_service.requests.get", fake_get)

    provider = BraveSearchProvider(
        api_key="test-key",
        endpoint="https://search.example.test",
        timeout_seconds=3.5,
    )
    result = provider.search(
        ResearchQuery(
            query="요즘 인기 김밥",
            locale="ko-KR",
            freshness_required=True,
            max_sources=4,
        )
    )

    assert calls[0]["url"] == "https://search.example.test"
    assert calls[0]["headers"]["X-Subscription-Token"] == "test-key"
    assert calls[0]["params"]["q"] == "요즘 인기 김밥"
    assert calls[0]["params"]["country"] == "KR"
    assert calls[0]["params"]["search_lang"] == "ko"
    assert calls[0]["params"]["freshness"] == "pd"
    assert calls[0]["params"]["count"] == 4
    assert calls[0]["timeout"] == 3.5
    assert result == [
        SearchCandidate(
            title="요즘 인기 김밥",
            url="https://example.com/kimbap",
            publisher="Example Food",
            published_at="2026-05-16",
            snippet="김밥 트렌드 간편식 인기",
        )
    ]


def test_search_provider_factory_uses_brave_only_when_configured(monkeypatch):
    monkeypatch.setattr(
        "app.services.live_research_service.config.LIVE_SEARCH_PROVIDER",
        "brave",
    )
    monkeypatch.setattr(
        "app.services.live_research_service.config.BRAVE_SEARCH_API_KEY",
        None,
    )

    assert isinstance(get_search_provider(), DisabledSearchProvider)

    monkeypatch.setattr(
        "app.services.live_research_service.config.BRAVE_SEARCH_API_KEY",
        "test-key",
    )

    assert isinstance(get_search_provider(), BraveSearchProvider)
