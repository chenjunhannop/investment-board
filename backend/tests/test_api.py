"""API 路由的单元测试：状态/登出与新闻已读接口."""
import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.api.ws import ws_router
from app.core.events import EventBus
from app.vault.store import Vault


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setattr("app.vault.store._keyring_get", lambda s, u: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda s, u, p: None)
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    app = FastAPI()
    vault = Vault(tmp_path)
    app.state.vault = vault
    app.state.bus = EventBus()
    app.state.scheduler = None
    app.state.ths = None
    app.include_router(router, prefix="/api")
    app.include_router(ws_router)
    return app


@pytest.mark.asyncio
async def test_status_and_logout(tmp_path, monkeypatch):
    """未登录时 /api/status 返回 200 且 logout 返回 ok."""
    app = _make_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.get("/api/status")
        assert r.status_code == 200
        body = r.json()
        assert body["logged_in"] is False
        assert "sources" in body

        r2 = await c.post("/api/logout")
        assert r2.json() == {"ok": True}


@pytest.mark.asyncio
async def test_mark_news_read(tmp_path, monkeypatch):
    """标记新闻已读接口返回 ok."""
    app = _make_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.post("/api/news/abc/read")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
