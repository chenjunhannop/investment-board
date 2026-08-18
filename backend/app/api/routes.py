"""REST 路由：状态、行情/新闻查询、新闻已读标记与本地自选管理."""
from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.core import watchlist

router = APIRouter()


@router.get("/status")
async def status():
    """返回各数据源状态，供前端展示顶部状态栏.

    Returns:
        含各数据源状态的字典（market/news 当前均为 ok）.
    """
    return {"sources": {"market": "ok", "news": "ok"}}


@router.get("/quotes")
async def get_quotes(request: Request):
    """返回调度器缓存的实时行情快照.

    Args:
        request: FastAPI 请求，携带挂载了 scheduler 的 app.state.

    Returns:
        代码到 Quote 的字典；调度器未启动时返回空字典.
    """
    sched = request.app.state.scheduler
    return sched.quotes if sched else {}


@router.get("/news")
async def get_news(request: Request, type: str = "all"):
    """返回新闻列表，可按类型过滤（individual 个股/global 全局）.

    Args:
        request: FastAPI 请求，携带挂载了 scheduler 的 app.state.
        type: 过滤类型，取值为 "all"/"individual"/"global".

    Returns:
        新闻条目列表；调度器未启动时返回空列表.
    """
    sched = request.app.state.scheduler
    if not sched:
        return []
    items = sched.news
    if type in ("individual", "global"):
        items = [i for i in items if i.news_type == type]
    return items


@router.post("/news/{news_id}/read")
async def mark_read(request: Request, news_id: str):
    """将指定新闻条目标记为已读.

    Args:
        request: FastAPI 请求，携带挂载了 scheduler 的 app.state.
        news_id: 新闻条目的唯一 id.

    Returns:
        {"ok": True}.
    """
    sched = request.app.state.scheduler
    if sched:
        for item in sched.news:
            if item.id == news_id:
                item.read = True
    return {"ok": True}


@router.get("/watchlist")
async def get_watchlist():
    """返回本地自选列表.

    Returns:
        自选列表 [{code, name}, ...].
    """
    return watchlist.load_watchlist(settings.data_dir)


@router.post("/watchlist")
async def add_watchlist_item(body: dict):
    """添加股票到自选列表.

    Args:
        body: 请求体，{"code": str}；name 可省略（显示层用行情补齐）.

    Returns:
        更新后的自选列表.

    Raises:
        HTTPException: 400 当代码格式非法.
    """
    code = (body or {}).get("code", "")
    try:
        return watchlist.add_watchlist(settings.data_dir, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/{code}")
async def remove_watchlist_item(code: str):
    """从自选列表删除股票.

    Args:
        code: 6 位股票代码.

    Returns:
        更新后的自选列表.
    """
    return watchlist.remove_watchlist(settings.data_dir, code)
