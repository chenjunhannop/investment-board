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
        try:
            published_at = _ts(item.get("notice_date", ""))
        except ValueError:
            continue  # 时间缺失/非法时跳过该条，不中断整体
        codes = [c.get("stock_code", "") for c in item.get("codes", [])]
        codes = [c for c in codes if c]
        art_code = item.get("art_code", "")
        # 东财公告详情页 URL（接口无直接 url 字段，用代码+art_code 拼接）
        url = ""
        if codes and art_code:
            url = f"https://data.eastmoney.com/notices/detail/{codes[0]}/{art_code}.html"
        out.append(
            NewsItem(
                id=art_code,
                source="eastmoney",
                title=item.get("title", ""),
                url=url,
                published_at=published_at,
                news_type="individual",
                related_codes=codes,
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
