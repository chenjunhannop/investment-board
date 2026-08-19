"""看板大屏聚合快照服务：合并指数/板块/资金/K线，30 秒 TTL 缓存."""
import logging
import time

import httpx

from app.market import sector

logger = logging.getLogger(__name__)

CACHE_TTL = 30.0


class DashboardService:
    """聚合大盘指数、板块排行、资金流与重点板块K线的大屏快照服务."""

    def __init__(self, client: httpx.AsyncClient, ttl: float = CACHE_TTL):
        """初始化快照服务.

        Args:
            client: 共享 httpx 客户端.
            ttl: 快照缓存有效期（秒），默认 30.
        """
        self._client = client
        self._ttl = ttl
        self._snapshot: dict = {}
        self._fetched_at: float = 0.0

    async def get_snapshot(self) -> dict:
        """返回大屏快照；缓存有效期内复用，过期或失败时降级保留上次.

        Returns:
            {"indices": [...], "market": {...}, "sectors": {...}, "kline": {...}}.
        """
        now = time.monotonic()
        if self._snapshot and now - self._fetched_at < self._ttl:
            return self._snapshot
        try:
            indices = await sector.fetch_indices(self._client)
            board = await sector.fetch_sector_board(self._client)
            top3_gainers = []
            for item in board["top_gainers"][:3]:
                top3_gainers.append({
                    "secid": item["secid"],
                    "name": item["name"],
                    "change_pct": item["change_pct"],
                    "klines": await sector.fetch_sector_kline(self._client, item["secid"]),
                })
            top3_losers = []
            for item in board["top_losers"][:3]:
                top3_losers.append({
                    "secid": item["secid"],
                    "name": item["name"],
                    "change_pct": item["change_pct"],
                    "klines": await sector.fetch_sector_kline(self._client, item["secid"]),
                })
            snapshot = {
                "indices": indices,
                "market": board["market"],
                "sectors": {
                    "top_gainers": board["top_gainers"],
                    "top_losers": board["top_losers"],
                    "fund_flow": board["fund_flow"],
                },
                "kline": {
                    "top3_gainers": top3_gainers,
                    "top3_losers": top3_losers
                },
            }
            self._snapshot = snapshot
            self._fetched_at = now
            return snapshot
        except Exception as e:
            # 抓取失败时降级：若已有缓存则返回缓存，否则返回空结构
            logger.warning("刷新大屏快照失败: %s", e)
            if self._snapshot:
                return self._snapshot
            return {
                "indices": [],
                "market": {
                    "up": 0,
                    "down": 0
                },
                "sectors": {
                    "top_gainers": [],
                    "top_losers": [],
                    "fund_flow": []
                },
                "kline": {
                    "top3_gainers": [],
                    "top3_losers": []
                }
            }
