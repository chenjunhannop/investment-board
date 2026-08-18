"""东方财富与财联社新闻接口的 JSON 解析器."""
import json
from datetime import datetime

from app.models import NewsItem


def _ts(iso: str) -> datetime:
    """把 ISO 时间字符串解析为 datetime（兼容空格分隔格式）.

    Args:
        iso: 形如 "2024-01-01 09:30:00" 的时间字符串.

    Returns:
        解析后的 datetime 对象.
    """
    return datetime.fromisoformat(iso.replace(" ", "T"))


def parse_eastmoney(text: str) -> list[NewsItem]:
    """解析东方财富个股公告接口返回的 JSON 文本.

    Args:
        text: 东方财富公告接口返回的 JSON 字符串.

    Returns:
        公告 NewsItem 列表；无公告数据时返回空列表.
    """
    data = json.loads(text)
    out: list[NewsItem] = []
    for item in data.get("data", {}).get("list", []):
        code = item.get("column_code", "").replace("sz", "").replace("sh", "")
        out.append(
            NewsItem(
                id=item.get("art_code", ""),
                source="eastmoney",
                title=item.get("notice_title", ""),
                url=item.get("art_url", ""),
                published_at=_ts(item.get("notice_date", "")),
                news_type="individual",
                related_codes=[code] if code else [],
            ))
    return out


def parse_cls(text: str) -> list[NewsItem]:
    """解析财联社电报（快讯）接口返回的 JSON 文本.

    Args:
        text: 财联社电报接口返回的 JSON 字符串.

    Returns:
        快讯 NewsItem 列表；无数据时返回空列表.
    """
    data = json.loads(text)
    out: list[NewsItem] = []
    for item in data.get("data", {}).get("roll_data", []):
        out.append(
            NewsItem(
                id=str(item.get("id", "")),
                source="cls",
                title=item.get("title", ""),
                url=item.get("share_url", ""),
                published_at=datetime.fromtimestamp(int(item.get("ctime", "0"))),
                news_type="global",
            ))
    return out
