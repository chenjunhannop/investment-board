"""后台调度器：以注入式 fetcher 周期抓取行情/新闻并通过事件总线发布.

各循环对单次抓取异常做兜底（记录日志后继续），避免单次网络抖动中断后台任务.
"""
import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.core.events import EventBus, EventType
from app.models import NewsItem, Quote

logger = logging.getLogger(__name__)

FETCHER = Callable[[list[str]], Awaitable[dict[str, Quote]]]


class Scheduler:
    """注入式 fetcher 的周期调度器，驱动行情/新闻两个后台循环."""

    def __init__(self,
                 bus: EventBus,
                 quotes_fetcher: FETCHER,
                 news_fetcher=None,
                 quotes_interval: float = 3.0,
                 news_interval: float = 60.0):
        """初始化调度器并保存各 fetcher 与周期配置.

        Args:
            bus: 事件总线，抓取结果经它发布.
            quotes_fetcher: 按代码列表抓取实时行情，返回代码到 Quote 的字典.
            news_fetcher: 按代码列表抓取新闻列表的可等待回调.
            quotes_interval: 行情轮询周期（秒）.
            news_interval: 新闻轮询周期（秒）.
        """
        self.bus = bus
        self._quotes_fetcher = quotes_fetcher
        self._news_fetcher = news_fetcher
        self.quotes_interval = quotes_interval
        self.news_interval = news_interval
        self.quotes: dict[str, Quote] = {}
        self.news: list[NewsItem] = []
        self.seen_news: set[str] = set()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def _spawn(self, coro) -> asyncio.Task:
        """将协程包装为后台任务并返回，便于集中取消."""
        return asyncio.create_task(coro)

    def start(self) -> None:
        """启动两个后台循环任务；已运行时直接返回（幂等）."""
        if self._running:
            return
        self._running = True
        self._tasks = [
            self._spawn(self._quotes_loop()),
            self._spawn(self._news_loop()),
        ]

    def stop(self) -> None:
        """停止调度：置运行标记为 False 并取消全部后台任务."""
        self._running = False
        for t in self._tasks:
            t.cancel()

    def _collect_codes(self) -> list[str]:
        """汇总本地自选代码与已有行情 key 的并集并排序返回."""
        from app.config import settings
        from app.core import watchlist

        codes = set(self.quotes.keys())
        codes.update(watchlist.collect_codes(settings.data_dir))
        return sorted(codes)

    async def _quotes_loop(self):
        """周期抓取行情并发布；异常仅记日志，等待下个周期重试."""
        while self._running:
            try:
                codes = self._collect_codes()
                # 无已知代码时也调用 fetcher（MarketService.fetch_quotes([]) 会安全返回空 dict），
                # 确保注入的 fetcher 总会被驱动、事件总能发布。
                self.quotes = await self._quotes_fetcher(codes)
                self.bus.publish(EventType.QUOTES, self.quotes)
            except Exception as e:
                # 网络抖动等偶发异常兜底：记录后继续，避免后台循环中断
                logger.warning("行情循环异常: %s", e)
            await asyncio.sleep(self.quotes_interval + random.uniform(0, 0.5))

    async def _news_loop(self):
        """周期抓取新闻，去重后保留最新 200 条并发布；异常仅记日志."""
        while self._running:
            if self._news_fetcher:
                try:
                    items = await self._news_fetcher(self._collect_codes())
                    fresh = [i for i in items if i.id not in self.seen_news]
                    self.seen_news.update(i.id for i in items)
                    if fresh:
                        self.news = fresh + self.news
                        self.news = self.news[:200]
                        self.bus.publish(EventType.NEWS, self.news)
                except Exception as e:
                    # 新闻抓取偶发失败兜底：记录后继续，避免后台循环中断
                    logger.warning("新闻循环异常: %s", e)
            await asyncio.sleep(self.news_interval)
