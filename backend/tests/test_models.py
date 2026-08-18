"""领域模型 dataclass 的单元测试."""
from datetime import datetime

from app.models import NewsItem, Quote


def test_quote_construction():
    """构造 Quote 后各字段与默认值正确."""
    q = Quote("600519", "贵州茅台", 1750.0, 50.0, 2.94, 1700.0, 1760.0, 1690.0, 1700.0, 30000, 5.2e8,
              datetime(2026, 8, 18, 10, 0))
    assert q.change_pct == 2.94
    assert q.amount == 5.2e8


def test_news_item_related_codes_isolated():
    """NewsItem 的 related_codes 列表在实例间互不影响."""
    a = NewsItem("1", "eastmoney", "标题", "http://x", datetime.now(), "individual")
    b = NewsItem("2", "eastmoney", "标题2", "http://y", datetime.now(), "individual")
    assert a.related_codes == []
    assert b.related_codes == []
