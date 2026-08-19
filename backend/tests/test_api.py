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


@pytest.mark.asyncio
async def test_watchlist_group_api(tmp_path, monkeypatch):
    """自选文件夹分组 API：建组/加股/删除/校验."""
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    app = _make_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        # 新建文件夹
        r = await c.post("/api/watchlist/groups", json={"name": "A"})
        assert r.status_code == 200
        assert r.json()["groups"] == [{"name": "A", "stocks": []}]
        # 重名 → 400
        r = await c.post("/api/watchlist/groups", json={"name": "A"})
        assert r.status_code == 400
        # 重命名
        r = await c.put("/api/watchlist/groups/A", json={"new_name": "B"})
        assert r.status_code == 200
        assert [g["name"] for g in r.json()["groups"]] == ["B"]
        # 添加股票
        r = await c.post("/api/watchlist/stocks", json={"group": "B", "code": "600519"})
        assert r.status_code == 200
        assert [s["code"] for s in r.json()["groups"][0]["stocks"]] == ["600519"]
        # 非法代码 → 400
        r = await c.post("/api/watchlist/stocks", json={"group": "B", "code": "abc"})
        assert r.status_code == 400
        # GET 返回分组结构
        r = await c.get("/api/watchlist")
        assert r.status_code == 200
        assert r.json()["version"] == 2
        assert len(r.json()["groups"]) == 1
        # 删除股票
        r = await c.delete("/api/watchlist/stocks/B/600519")
        assert r.status_code == 200
        assert r.json()["groups"][0]["stocks"] == []
        # 删除文件夹
        r = await c.delete("/api/watchlist/groups/B")
        assert r.status_code == 200
        assert r.json()["groups"] == []
