"""核心层（事件总线/调度器）的单元测试."""
import asyncio
from datetime import datetime

import pytest

from app.core.events import EventBus
from app.core.scheduler import Scheduler
from app.models import Quote


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


def test_scheduler_collect_codes_includes_watchlist(tmp_path, monkeypatch):
    """_collect_codes 汇总本地自选代码与已有行情 key 的并集."""
    import json

    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "watchlist.json").write_text(
        json.dumps([{"code": "000001", "name": "平安银行"}]), encoding="utf-8"
    )
    bus = EventBus()
    sched = Scheduler(bus, quotes_fetcher=None)
    sched.quotes = {
        "600519": Quote("600519", "贵州茅台", 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, datetime.now())
    }
    assert sched._collect_codes() == ["000001", "600519"]
