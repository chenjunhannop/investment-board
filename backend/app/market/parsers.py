# backend/app/market/parsers.py
import re
from datetime import datetime

from app.models import IntradayPoint, Quote


def _today() -> datetime:
    return datetime.now().replace(microsecond=0)


def parse_sina(text: str) -> Quote:
    m = re.search(r'="(.*)";', text)
    if not m:
        raise ValueError("bad sina payload")
    f = m.group(1).split(",")
    prev_close = float(f[2])
    price = float(f[3])
    return Quote(
        code=text.split("hq_str_")[1].split("=")[0][2:],  # "sh600519" -> "600519"
        name=f[0],
        price=price,
        change=round(price - prev_close, 3),
        change_pct=round((price - prev_close) / prev_close * 100, 2),
        open=float(f[1]),
        high=float(f[4]),
        low=float(f[5]),
        prev_close=prev_close,
        volume=float(f[8]) / 100,
        amount=float(f[9]),
        ts=_today(),
    )


def parse_tencent(text: str) -> Quote:
    m = re.search(r'="(.*)";', text)
    f = m.group(1).split("~")
    prev_close = float(f[4])
    price = float(f[3])
    return Quote(
        code=f[2],
        name=f[1],
        price=price,
        change=round(price - prev_close, 3),
        change_pct=float(f[32]),
        open=float(f[5]),
        high=float(f[33]),
        low=float(f[34]),
        prev_close=prev_close,
        volume=float(f[6]),
        amount=float(f[37]) * 1e4,
        ts=_today(),
    )


def parse_sina_intraday(text: str) -> list[IntradayPoint]:
    pts = []
    for line in text.strip().splitlines():
        if "=" in line or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 4:
            continue
        pts.append(
            IntradayPoint(
                time=parts[1],
                price=float(parts[2]),
                avg_price=float(parts[3]),
                volume=float(parts[4]) if len(parts) > 4 else 0.0,
            ))
    return pts
