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

    def subscribe(self, event_type: str, cb: Sub) -> None:
        self._subs.setdefault(event_type, []).append(cb)

    def publish(self, event_type: str, payload: Any) -> None:
        for cb in self._subs.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass
