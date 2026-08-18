"""API 路由的单元测试：状态与新闻已读接口."""
import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import router
from app.api.ws import ws_router
from app.core.events import EventBus


def _make_app():
    app = FastAPI()
    app.state.bus = EventBus()
    app.state.scheduler = None
    app.include_router(router, prefix="/api")
    app.include_router(ws_router)
    return app


@pytest.mark.asyncio
async def test_status_sources():
    """状态接口返回 market/news 数据源状态."""
    app = _make_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.get("/api/status")
        assert r.status_code == 200
        assert r.json() == {"sources": {"market": "ok", "news": "ok"}}


@pytest.mark.asyncio
async def test_mark_news_read():
    """标记新闻已读接口返回 ok."""
    app = _make_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.post("/api/news/abc/read")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
