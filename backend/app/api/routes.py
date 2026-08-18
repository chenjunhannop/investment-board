"""REST 路由：状态、登录/登出、行情/持仓/新闻查询与新闻已读标记."""
from fastapi import APIRouter, HTTPException, Request

from app.core.portfolio import compute_positions

router = APIRouter()


@router.get("/status")
async def status(request: Request):
    """返回服务与登录状态，供前端展示顶部状态栏.

    Args:
        request: FastAPI 请求，携带挂载了 vault 的 app.state.

    Returns:
        含 logged_in 与各数据源/同花顺状态字段的字典.
    """
    vault = request.app.state.vault
    return {
        "logged_in": vault.is_logged_in,
        "sources": {
            "market": "ok",
            "news": "ok"
        },
        "ths": {
            "status": "ok" if vault.is_logged_in else "not_logged_in"
        },
    }


@router.post("/login/qrcode")
async def login_qrcode(request: Request):
    """获取同花顺登录二维码数据.

    Args:
        request: FastAPI 请求，携带挂载了 ths 的 app.state.

    Returns:
        包含二维码数据的字典.

    Raises:
        HTTPException: 503 当同花顺客户端未注入（测试/未配置采集器）.
    """
    ths = request.app.state.ths
    if ths is None:
        # ths 未配置（测试/未注入采集器）时返回 503 而非 500
        raise HTTPException(status_code=503, detail="THS 客户端未配置")
    return await ths.login_qrcode()


@router.post("/login/poll")
async def login_poll(request: Request):
    """轮询同花顺扫码登录结果.

    Args:
        request: FastAPI 请求，携带挂载了 ths 的 app.state.

    Returns:
        {"ok": bool}，表示本次轮询是否已完成登录.

    Raises:
        HTTPException: 503 当同花顺客户端未注入.
    """
    ths = request.app.state.ths
    if ths is None:
        raise HTTPException(status_code=503, detail="THS 客户端未配置")
    return {"ok": await ths.poll_login()}


@router.post("/logout")
async def logout(request: Request):
    """登出同花顺并清除本地会话凭据.

    Args:
        request: FastAPI 请求，携带挂载了 ths 的 app.state.

    Returns:
        {"ok": True}.
    """
    ths = request.app.state.ths
    if ths:
        await ths.logout()
    return {"ok": True}


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


@router.get("/positions")
async def get_positions(request: Request):
    """返回绑定实时行情后的持仓列表.

    Args:
        request: FastAPI 请求，携带挂载了 scheduler 的 app.state.

    Returns:
        持仓列表；调度器未启动时返回空列表.
    """
    sched = request.app.state.scheduler
    if not sched:
        return []
    return compute_positions(sched.positions, sched.quotes)


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
