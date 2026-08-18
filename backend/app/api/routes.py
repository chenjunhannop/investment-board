# backend/app/api/routes.py
from fastapi import APIRouter, HTTPException, Request

from app.core.portfolio import compute_positions

router = APIRouter()


@router.get("/status")
async def status(request: Request):
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
    ths = request.app.state.ths
    if ths is None:
        # ths 未配置（测试/未注入采集器）时返回 503 而非 500
        raise HTTPException(status_code=503, detail="THS 客户端未配置")
    return await ths.login_qrcode()


@router.post("/login/poll")
async def login_poll(request: Request):
    ths = request.app.state.ths
    if ths is None:
        raise HTTPException(status_code=503, detail="THS 客户端未配置")
    return {"ok": await ths.poll_login()}


@router.post("/logout")
async def logout(request: Request):
    ths = request.app.state.ths
    if ths:
        await ths.logout()
    return {"ok": True}


@router.get("/quotes")
async def get_quotes(request: Request):
    sched = request.app.state.scheduler
    return sched.quotes if sched else {}


@router.get("/positions")
async def get_positions(request: Request):
    sched = request.app.state.scheduler
    if not sched:
        return []
    return compute_positions(sched.positions, sched.quotes)


@router.get("/news")
async def get_news(request: Request, type: str = "all"):
    sched = request.app.state.scheduler
    if not sched:
        return []
    items = sched.news
    if type in ("individual", "global"):
        items = [i for i in items if i.news_type == type]
    return items


@router.post("/news/{news_id}/read")
async def mark_read(request: Request, news_id: str):
    sched = request.app.state.scheduler
    if sched:
        for item in sched.news:
            if item.id == news_id:
                item.read = True
    return {"ok": True}
