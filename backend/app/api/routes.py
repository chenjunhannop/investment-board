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
    """返回本地自选列表（文件夹分组结构）.

    Returns:
        {"version": 2, "groups": [{"name", "stocks"}]}.
    """
    return watchlist.load_watchlist(settings.data_dir)


@router.post("/watchlist/groups")
async def add_group(body: dict):
    """新建自选文件夹.

    Args:
        body: {"name": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当名称为空或重名.
    """
    try:
        return watchlist.add_group(settings.data_dir, (body or {}).get("name", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/watchlist/groups/{name}")
async def rename_group(name: str, body: dict):
    """重命名自选文件夹.

    Args:
        name: 当前文件夹名.
        body: {"new_name": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹不存在或新名非法.
    """
    try:
        return watchlist.rename_group(settings.data_dir, name,
                                      (body or {}).get("new_name", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/groups/{name}")
async def remove_group(name: str):
    """删除自选文件夹（连带其股票）.

    Args:
        name: 文件夹名.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹不存在.
    """
    try:
        return watchlist.remove_group(settings.data_dir, name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/watchlist/stocks")
async def add_stock(body: dict):
    """向指定文件夹添加股票.

    Args:
        body: {"group": str, "code": str}.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当代码非法或文件夹不存在.
    """
    body = body or {}
    try:
        return watchlist.add_stock(settings.data_dir, body.get("group", ""),
                                   body.get("code", ""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/watchlist/stocks/{group}/{code}")
async def remove_stock(group: str, code: str):
    """从指定文件夹删除股票.

    Args:
        group: 文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        HTTPException: 400 当文件夹或股票不存在.
    """
    try:
        return watchlist.remove_stock(settings.data_dir, group, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
