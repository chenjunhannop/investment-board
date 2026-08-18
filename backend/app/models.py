"""领域数据模型：自选股、实时行情、日内分时与新闻条目.

全部为轻量 dataclass，仅承载数据不含业务逻辑；字段契约保持稳定.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Stock:
    """一只自选股的基础信息."""

    code: str  # "600519"
    name: str  # "贵州茅台"
    market: str = "SH"  # "SH" / "SZ"


@dataclass
class Quote:
    """一条实时行情快照."""

    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float  # 手
    amount: float  # 元
    ts: datetime


@dataclass
class IntradayPoint:
    """一个日内分时数据点."""

    time: str  # "09:30"
    price: float
    avg_price: float
    volume: float


@dataclass
class NewsItem:
    """一条新闻条目（个股公告或全局快讯）."""

    id: str
    source: str  # "eastmoney" / "cls"
    title: str
    url: str
    published_at: datetime
    news_type: str  # "individual" / "global"
    related_codes: list[str] = field(default_factory=list)
    read: bool = False
