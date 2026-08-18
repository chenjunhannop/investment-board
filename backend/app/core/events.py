from typing import Any, Callable

Sub = Callable[[Any], None]


class EventType:
    QUOTES = "quotes"
    POSITIONS = "positions"
    NEWS = "news"
    THS_STATUS = "ths_status"
    SOURCE_STATUS = "source_status"


class EventBus:
    def __init__(self):
        self._subs: dict[str, list[Sub]] = {}

    def subscribe(self, event_type: str, cb: Sub) -> Sub:
        # 返回回调本身，便于订阅方在连接关闭时调用 unsubscribe 释放
        self._subs.setdefault(event_type, []).append(cb)
        return cb

    def unsubscribe(self, event_type: str, cb: Sub) -> None:
        subs = self._subs.get(event_type)
        if subs and cb in subs:
            subs.remove(cb)

    def publish(self, event_type: str, payload: Any) -> None:
        for cb in self._subs.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass
