from types import SimpleNamespace

from scripts import scrape_10000recipe


class FakeDb:
    def close(self):
        pass


def run_scraper(monkeypatch, args: list[str], exists: bool) -> dict[str, int]:
    calls = {"scrape": 0, "save": 0}

    monkeypatch.setattr(
        scrape_10000recipe.argparse.ArgumentParser,
        "parse_args",
        lambda _: SimpleNamespace(
            limit=1,
            start_page=1,
            delay_min=0,
            delay_max=0,
            force="--force" in args,
            resume="--resume" in args,
            dry_run=False,
        ),
    )
    monkeypatch.setattr(scrape_10000recipe, "SessionLocal", lambda: FakeDb())
    monkeypatch.setattr(
        scrape_10000recipe,
        "fetch_recipe_ids",
        lambda page: ["123"] if page == 1 else [],
    )
    monkeypatch.setattr(scrape_10000recipe, "already_exists", lambda db, rid: exists)
    monkeypatch.setattr(scrape_10000recipe.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(scrape_10000recipe.random, "uniform", lambda start, end: 0)

    def fake_scrape(recipe_id: str):
        calls["scrape"] += 1
        return {
            "source_recipe_id": recipe_id,
            "source_url": f"https://example.com/{recipe_id}",
            "title": "테스트 레시피",
            "author": {"name": "", "url": ""},
        }

    def fake_save(db, raw, dry_run):
        calls["save"] += 1

    monkeypatch.setattr(scrape_10000recipe, "scrape_recipe", fake_scrape)
    monkeypatch.setattr(scrape_10000recipe, "save_source", fake_save)

    scrape_10000recipe.main()
    return calls


def test_scraper_skips_existing_recipe_by_default(monkeypatch):
    calls = run_scraper(monkeypatch, args=[], exists=True)

    assert calls == {"scrape": 0, "save": 0}


def test_scraper_force_requests_existing_recipe(monkeypatch):
    calls = run_scraper(monkeypatch, args=["--force"], exists=True)

    assert calls == {"scrape": 1, "save": 1}
