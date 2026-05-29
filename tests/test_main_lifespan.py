import pytest

from app import main


@pytest.mark.anyio
async def test_lifespan_raises_when_database_initialization_fails(monkeypatch):
    def fail_init_db():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main, "init_db", fail_init_db)

    with pytest.raises(RuntimeError, match="database unavailable"):
        async with main.lifespan(main.app):
            pass
