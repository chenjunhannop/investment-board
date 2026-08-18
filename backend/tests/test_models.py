# backend/tests/test_models.py
from datetime import datetime

from app.models import NewsItem, Position, Quote


def test_quote_construction():
    q = Quote("600519", "贵州茅台", 1750.0, 50.0, 2.94, 1700.0, 1760.0, 1690.0, 1700.0, 30000, 5.2e8,
              datetime(2026, 8, 18, 10, 0))
    assert q.change_pct == 2.94
    assert q.amount == 5.2e8


def test_position_defaults():
    p = Position("000001", "平安银行", 1000, 12.0)
    assert p.market_value == 0.0
    assert p.profit == 0.0


def test_news_item_related_codes_isolated():
    a = NewsItem("1", "eastmoney", "标题", "http://x", datetime.now(), "individual")
    b = NewsItem("2", "eastmoney", "标题2", "http://y", datetime.now(), "individual")
    assert a.related_codes == []
    assert b.related_codes == []
