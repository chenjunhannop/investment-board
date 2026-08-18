# backend/app/api/ws.py
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import EventType

logger = logging.getLogger(__name__)
ws_router = APIRouter()

# 需要向客户端推送的全部事件类型
_EVENTS = (EventType.QUOTES, EventType.POSITIONS, EventType.NEWS,
           EventType.THS_STATUS, EventType.SOURCE_STATUS)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)


manager = ConnectionManager()


@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # 直接从 app.state 取依赖，避免 WebSocket 的 Depends 坑
    bus = ws.app.state.bus
    await manager.connect(ws)

    # 每个连接只向自己推送：若每个订阅都向全部连接广播，则 N 个连接时
    # 每一条事件会被推 N 份，且每个事件产生 O(N^2) 个任务。
    # 改为每个订阅只推给自己：一条事件恰好产生一个任务、每个连接恰好一份。
    def _subscribe(et: str):
        async def _send(payload):
            try:
                await ws.send_json({"type": et, "data": payload})
            except Exception:
                # 连接已断开（半开连接/竞态），从活跃集合移除
                manager.disconnect(ws)

        return lambda payload: asyncio.create_task(_send(payload))

    # 记录订阅回调，连接关闭时从总线移除，防止事件总线回调泄漏
    subs = [(et, bus.subscribe(et, _subscribe(et))) for et in _EVENTS]
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        for et, cb in subs:
            bus.unsubscribe(et, cb)
        manager.disconnect(ws)
