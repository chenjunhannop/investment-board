"""新浪/腾讯行情接口的文本解析器.

提供对行情接口返回文本的解析函数，失败时统一抛出 ValueError.
"""
import re
from datetime import datetime

from app.models import IntradayPoint, Quote


def _today() -> datetime:
    """返回去除微秒的当前时间，作为行情快照时间戳."""
    return datetime.now().replace(microsecond=0)


def parse_sina(text: str) -> Quote:
    """解析新浪行情接口返回文本为实时行情快照.

    Args:
        text: 新浪行情接口返回的单行文本.

    Returns:
        解析得到的 Quote 快照.

    Raises:
        ValueError: 文本缺少行情载荷（无法匹配 `="...";` 片段）时抛出.
    """
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
    """解析腾讯行情接口返回文本为实时行情快照.

    Args:
        text: 腾讯行情接口返回的单行文本.

    Returns:
        解析得到的 Quote 快照.

    Raises:
        ValueError: 文本缺少行情载荷（无法匹配 `="...";` 片段）时抛出.
    """
    m = re.search(r'="(.*)";', text)
    if not m:
        raise ValueError("bad tencent payload")
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
    """解析新浪日内分时接口返回文本为分时数据点列表.

    Args:
        text: 新浪分时接口返回的多行文本.

    Returns:
        分时数据点列表；无实际数据的行会被跳过.
    """
    pts: list[IntradayPoint] = []
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
