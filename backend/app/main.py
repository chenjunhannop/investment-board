"""FastAPI 应用装配：lifespan 启动各服务与调度器，提供 uvicorn main() 入口."""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.ws import ws_router
from app.config import settings
from app.core.events import EventBus
from app.core.scheduler import Scheduler
from app.market.service import MarketService
from app.news.service import NewsService
from app.ths_client.web_client import ThsWebClient
from app.vault.store import Vault

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时装配各服务并启动调度器，关闭时停止并清理连接.

    Args:
        app: 正在启动/关闭的 FastAPI 实例，运行期间挂载 vault/ths/bus/scheduler.
    """
    client = httpx.AsyncClient()
    vault = Vault(settings.data_dir)
    market = MarketService(client)
    news = NewsService(client)
    ths = ThsWebClient(vault,
                       client,
                       settings.ths_endpoint_prefix,
                       watchlist_url=settings.ths_watchlist_url,
                       positions_url=settings.ths_positions_url)
    bus = EventBus()

    async def positions_fetcher():
        """抓取同花顺持仓，未登录时返回空列表."""
        if ths.is_logged_in:
            return await ths.query_positions()
        return []

    async def news_fetcher(codes):
        """抓取个股公告与全局快讯，未登录时仅返回全局快讯.

        Args:
            codes: 需要拉取公告的股票代码列表.

        Returns:
            个股公告与全局快讯的合并列表.
        """
        ind = await news.fetch_individual(codes) if ths.is_logged_in else []
        glb = await news.fetch_global()
        return ind + glb

    sched = Scheduler(
        bus,
        quotes_fetcher=market.fetch_quotes,
        positions_fetcher=positions_fetcher,
        news_fetcher=news_fetcher,
        quotes_interval=settings.quotes_interval,
        positions_interval=settings.positions_interval,
        news_interval=settings.news_interval,
        ths_adapter=ths,
    )
    app.state.vault = vault
    app.state.ths = ths
    app.state.bus = bus
    app.state.scheduler = sched
    sched.start()
    yield
    sched.stop()
    await client.aclose()


app = FastAPI(title="Investment Board", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_methods=["*"],
                   allow_headers=["*"])
app.include_router(router, prefix="/api")
app.include_router(ws_router)


def main() -> None:
    """启动 uvicorn 开发服务器（仅监听本机）."""
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
