"""核心层（事件总线/持仓计算/调度器）的单元测试."""
import asyncio
from datetime import datetime

import pytest

from app.core.events import EventBus
from app.core.portfolio import compute_positions
from app.core.scheduler import Scheduler
from app.models import Position, Quote


def test_compute_positions():
    """绑定行情后计算市值/盈亏与涨跌百分比."""
    p = Position("600519", "贵州茅台", 100, 1600.0, available=100)
    q = Quote("600519", "贵州茅台", 1750.0, 50.0, 3.125, 1700.0, 1760.0, 1690.0, 1700.0, 0, 0,
              datetime.now())
    out = compute_positions([p], {"600519": q})
    assert out[0].current_price == 1750.0
    assert out[0].market_value == 175000.0
    assert out[0].profit == 15000.0
    assert round(out[0].profit_pct, 2) == 9.38


def test_compute_positions_keeps_missing_quote():
    """无匹配行情时持仓字段保持默认值."""
    p = Position("000001", "平安银行", 100, 10.0)
    out = compute_positions([p], {})
    assert out[0].profit == 0.0


def test_event_bus_dispatch():
    """订阅者能收到 publish 分发的载荷."""
    bus = EventBus()
    got = []
    bus.subscribe("QUOTES", lambda p: got.append(p))
    bus.publish("QUOTES", {"x": 1})
    assert got == [{"x": 1}]


@pytest.mark.asyncio
async def test_scheduler_quotes_loop_publishes():
    """调度器行情循环会周期发布行情事件."""

    async def fetch_quotes(codes):
        return {
            "600519": Quote("600519", "贵州茅台", 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, datetime.now())
        }

    bus = EventBus()
    published = []
    bus.subscribe("quotes", lambda p: published.append(p))
    sched = Scheduler(bus, quotes_fetcher=fetch_quotes, quotes_interval=0.05)
    sched.start()
    await asyncio.sleep(0.15)
    sched.stop()
    assert len(published) >= 1
    assert "600519" in published[0]
