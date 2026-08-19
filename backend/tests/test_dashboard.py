"""看板大屏快照服务的单元测试."""
from unittest.mock import AsyncMock, patch

import pytest

from app.market.dashboard import DashboardService


@pytest.mark.asyncio
async def test_dashboard_ttl_and_degrade():
    """TTL 内复用缓存；失败时降级保留上次快照."""
    client = AsyncMock()
    svc = DashboardService(client, ttl=30.0)
    with patch("app.market.sector.fetch_indices", AsyncMock(return_value=[{"name": "上证指数"}])) as fi, \
         patch("app.market.sector.fetch_sector_board",
               AsyncMock(return_value={"top_gainers": [{"secid": "90.BK1", "name": "A", "change_pct": 1.0}],
                                       "top_losers": [], "fund_flow": [],
                                       "market": {"up": 1, "down": 0}})) as fb, \
         patch("app.market.sector.fetch_sector_kline", AsyncMock(return_value=[["2026-08-18", 1, 2, 3, 4, 5, 6]])):
        snap1 = await svc.get_snapshot()
        assert snap1["indices"][0]["name"] == "上证指数"
        assert len(snap1["kline"]["top3_gainers"]) == 1
        snap2 = await svc.get_snapshot()  # TTL 内命中缓存，不重新抓取
        assert fi.await_count == 1
        assert fb.await_count == 1
        assert snap2 == snap1
        # 模拟后续失败：清缓存后强制失败，应返回上次快照
        svc._fetched_at = 0
        svc._snapshot = snap1
        fb.side_effect = Exception("network")
        snap3 = await svc.get_snapshot()
        assert snap3 == snap1
