# backend/app/news/parsers.py
import json
from datetime import datetime

from app.models import NewsItem


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace(" ", "T"))


def parse_eastmoney(text: str) -> list[NewsItem]:
    data = json.loads(text)
    out = []
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
    data = json.loads(text)
    out = []
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
