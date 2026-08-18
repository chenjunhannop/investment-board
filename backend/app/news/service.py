"""新闻服务：拉取个股公告与全局快讯，并按 id 去重."""
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
    """新闻服务：个股公告 + 全局快讯获取，附带去重."""

    def __init__(self, client: httpx.AsyncClient, timeout: float = 10.0):
        """初始化新闻服务.

        Args:
            client: 共享的 httpx 异步客户端.
            timeout: 单次请求超时秒数，默认 10 秒.
        """
        self._client = client
        self._timeout = timeout

    async def fetch_individual(self, codes: list[str]) -> list[NewsItem]:
        """按代码列表抓取个股公告.

        Args:
            codes: 6 位股票代码列表.

        Returns:
            公告 NewsItem 列表；单只股票失败会被跳过，不中断整体.
        """
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
        """抓取财联社全局快讯.

        Returns:
            快讯 NewsItem 列表；获取失败时返回空列表.
        """
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
        """按 id 去重：返回不在 seen_ids 中的条目，并把本次条目 id 并入 seen_ids.

        Args:
            items: 待去重的新闻条目列表.
            seen_ids: 已见 id 集合（原地更新）.

        Returns:
            未见过的新条目列表.
        """
        fresh = [i for i in items if i.id not in seen_ids]
        seen_ids.update(i.id for i in items)
        return fresh
