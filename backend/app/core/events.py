"""进程内事件总线：调度器发布行情/新闻事件，订阅方按类型接收."""
from collections.abc import Callable
from typing import Any

Sub = Callable[[Any], None]


class EventType:
    """事件类型常量集合，作为 publish/subscribe 的事件名."""

    QUOTES = "quotes"
    NEWS = "news"
    SOURCE_STATUS = "source_status"


class EventBus:
    """同步事件总线，按事件类型维护回调列表并逐个分发."""

    def __init__(self):
        """初始化空的事件类型到回调列表的映射."""
        self._subs: dict[str, list[Sub]] = {}

    def subscribe(self, event_type: str, cb: Sub) -> Sub:
        """订阅某类事件，返回回调本身便于后续解绑.

        Args:
            event_type: 事件类型名，取自 EventType 常量.
            cb: 事件发生时以 payload 为唯一参数调用的回调.

        Returns:
            传入的 cb，供订阅方在连接关闭时调用 unsubscribe 释放.
        """
        # 返回回调本身，便于订阅方在连接关闭时调用 unsubscribe 释放
        self._subs.setdefault(event_type, []).append(cb)
        return cb

    def unsubscribe(self, event_type: str, cb: Sub) -> None:
        """取消订阅，从对应事件类型的回调列表中移除 cb.

        Args:
            event_type: 事件类型名.
            cb: 先前 subscribe 时传入并返回的回调.
        """
        subs = self._subs.get(event_type)
        if subs and cb in subs:
            subs.remove(cb)

    def publish(self, event_type: str, payload: Any) -> None:
        """向某事件类型的全部订阅者分发 payload，单个回调异常被吞掉.

        Args:
            event_type: 事件类型名.
            payload: 随事件携带的数据，类型随事件而定.
        """
        for cb in self._subs.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass
