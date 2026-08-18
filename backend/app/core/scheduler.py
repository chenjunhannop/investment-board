import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from app.core.events import EventBus, EventType
from app.models import NewsItem, Position, Quote

logger = logging.getLogger(__name__)

FETCHER = Callable[[list[str]], Awaitable[dict[str, Quote]]]


class Scheduler:
    def __init__(self, bus: EventBus,
                 quotes_fetcher: FETCHER,
                 positions_fetcher=None,
                 news_fetcher=None,
                 quotes_interval: float = 3.0,
                 positions_interval: float = 10.0,
                 news_interval: float = 60.0,
                 ths_adapter=None):
        self.bus = bus
        self._quotes_fetcher = quotes_fetcher
        self._positions_fetcher = positions_fetcher
        self._news_fetcher = news_fetcher
        self._ths = ths_adapter
        self.quotes_interval = quotes_interval
        self.positions_interval = positions_interval
        self.news_interval = news_interval
        self.quotes: dict[str, Quote] = {}
        self.positions: list[Position] = []
        self.news: list[NewsItem] = []
        self.seen_news: set[str] = set()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def _spawn(self, coro) -> asyncio.Task:
        return asyncio.create_task(coro)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            self._spawn(self._quotes_loop()),
            self._spawn(self._positions_loop()),
            self._spawn(self._news_loop()),
        ]

    def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()

    def _collect_codes(self) -> list[str]:
        codes = set(self.quotes.keys())
        for p in self.positions:
            codes.add(p.code)
        return sorted(codes)

    async def _quotes_loop(self):
        while self._running:
            try:
                codes = self._collect_codes()
                # 无已知代码时也调用 fetcher（MarketService.fetch_quotes([]) 会安全返回空 dict），
                # 确保注入的 fetcher 总会被驱动、事件总能发布。
                self.quotes = await self._quotes_fetcher(codes)
                self.bus.publish(EventType.QUOTES, self.quotes)
            except Exception as e:
                logger.warning("行情循环异常: %s", e)
            await asyncio.sleep(self.quotes_interval + random.uniform(0, 0.5))

    async def _positions_loop(self):
        while self._running:
            if self._positions_fetcher and self._ths and self._ths.is_logged_in:
                try:
                    self.positions = await self._positions_fetcher()
                    enriched = self._apply_quotes(self.positions)
                    self.bus.publish(EventType.POSITIONS, enriched)
                except Exception as e:
                    logger.warning("持仓循环异常: %s", e)
                    self.bus.publish(EventType.THS_STATUS,
                                     {"status": "error", "message": str(e)})
            await asyncio.sleep(self.positions_interval)

    def _apply_quotes(self, pos: list[Position]) -> list[Position]:
        from app.core.portfolio import compute_positions
        return compute_positions(pos, self.quotes)

    async def _news_loop(self):
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
                    logger.warning("新闻循环异常: %s", e)
            await asyncio.sleep(self.news_interval)
