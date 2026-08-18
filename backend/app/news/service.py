# backend/app/news/service.py
import logging

import httpx

from app.models import NewsItem
from app.news.parsers import parse_cls, parse_eastmoney

logger = logging.getLogger(__name__)

EM_NOTICE_URL = ("https://np-anotice-stock.eastmoney.com/api/security/ann"
                 "?sr=-1&page_size=20&page_index=1&ann_type=A&client_source=web&"
                 "stock_list={code}")
CLS_TELEGRAPH_URL = "https://www.cls.cn/nodeapi/telegraphList?app=CailianpressWeb"


class NewsService:

    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        self._client = client
        self._timeout = timeout

    async def fetch_individual(self, codes: list[str]) -> list[NewsItem]:
        out: list[NewsItem] = []
        for code in codes:
            try:
                r = await self._client.get(EM_NOTICE_URL.format(code=code),
                                           timeout=self._timeout,
                                           headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                for item in parse_eastmoney(r.text):
                    if code not in item.related_codes:
                        item.related_codes = [code]
                    out.append(item)
            except Exception as e:
                logger.warning("个股公告获取失败 %s: %s", code, e)
        return out

    async def fetch_global(self) -> list[NewsItem]:
        try:
            r = await self._client.get(CLS_TELEGRAPH_URL,
                                       timeout=self._timeout,
                                       headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return parse_cls(r.text)
        except Exception as e:
            logger.warning("全局快讯获取失败: %s", e)
            return []

    def dedupe(self, items: list[NewsItem], seen_ids: set[str]) -> list[NewsItem]:
        fresh = [i for i in items if i.id not in seen_ids]
        seen_ids.update(i.id for i in items)
        return fresh
