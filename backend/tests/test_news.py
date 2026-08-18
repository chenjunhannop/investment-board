# backend/tests/test_news.py
from datetime import datetime

import httpx
import pytest
from respx import MockRouter

from app.models import NewsItem
from app.news.parsers import parse_cls, parse_eastmoney
from app.news.service import NewsService

EM_FIXTURE = """{
  "data": {
    "list": [
      {"art_code": "A001", "notice_title": "贵州茅台2026年半年度报告",
       "notice_date": "2026-08-18 09:00:00",
       "column_code": "sz000001",
       "art_url": "http://static.cninfo.com.cn/xxx.pdf"}
    ]
  }
}"""

CLS_FIXTURE = """{
  "data": {
    "roll_data": [
      {"id": 1001, "title": "【快讯】两市成交额突破万亿",
       "ctime": "1723950000",
       "share_url": "https://www.cls.cn/detail/1001"}
    ]
  }
}"""


def test_parse_eastmoney():
    items = parse_eastmoney(EM_FIXTURE)
    assert items[0].news_type == "individual"
    assert items[0].related_codes == ["000001"]
    assert items[0].source == "eastmoney"


def test_parse_cls():
    items = parse_cls(CLS_FIXTURE)
    assert items[0].news_type == "global"
    assert items[0].source == "cls"


def _stub(i: str) -> NewsItem:
    return NewsItem(i, "cls", "t", "u", datetime.now(), "global")


def test_dedupe_keeps_new():
    svc = NewsService(httpx.AsyncClient())
    new = svc.dedupe([_stub("1"), _stub("2")], seen_ids={"1"})
    assert [i.id for i in new] == ["2"]


@pytest.mark.asyncio
async def test_fetch_individual_maps_related_code(respx_mock: MockRouter):
    from app.news.service import EM_NOTICE_URL
    respx_mock.get(
        EM_NOTICE_URL.format(code="000001")).mock(return_value=httpx.Response(200, text=EM_FIXTURE))
    svc = NewsService(httpx.AsyncClient())
    items = await svc.fetch_individual(["000001"])
    assert len(items) == 1
    assert items[0].news_type == "individual"
    assert items[0].source == "eastmoney"
    assert "000001" in items[0].related_codes
