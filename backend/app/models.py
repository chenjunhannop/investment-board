# backend/app/models.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Stock:
    code: str  # "600519"
    name: str  # "贵州茅台"
    market: str = "SH"  # "SH" / "SZ"


@dataclass
class Position:
    code: str
    name: str
    quantity: int  # 持股数量(股)
    cost_price: float  # 成本价
    available: int = 0  # 可用数量
    current_price: float = 0.0
    market_value: float = 0.0
    profit: float = 0.0
    profit_pct: float = 0.0
    day_change: float = 0.0
    day_change_pct: float = 0.0


@dataclass
class Quote:
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
    time: str  # "09:30"
    price: float
    avg_price: float
    volume: float


@dataclass
class NewsItem:
    id: str
    source: str  # "eastmoney" / "cls"
    title: str
    url: str
    published_at: datetime
    news_type: str  # "individual" / "global"
    related_codes: list[str] = field(default_factory=list)
    read: bool = False
