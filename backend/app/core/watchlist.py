"""本地自选股列表的加载/添加/删除（JSON 文件持久化，含并发锁与原子写）."""
import json
import re
import threading
from pathlib import Path

_FILENAME = "watchlist.json"
_lock = threading.Lock()


def _path(data_dir: Path) -> Path:
    """返回自选列表文件路径.

    Args:
        data_dir: 数据目录.

    Returns:
        data_dir 下的 watchlist.json 路径.
    """
    return data_dir / _FILENAME


def load_watchlist(data_dir: Path) -> list[dict]:
    """读取本地自选列表.

    Args:
        data_dir: 数据目录.

    Returns:
        自选列表 [{code, name}, ...]；文件不存在返回空列表.
    """
    p = _path(data_dir)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [i for i in data if isinstance(i, dict) and i.get("code")]
        return []
    except (json.JSONDecodeError, OSError):
        # 损坏时备份原文件并返回空列表，避免服务不可用
        try:
            p.rename(p.with_suffix(".json.bak"))
        except OSError:
            pass
        return []


def add_watchlist(data_dir: Path, code: str, name: str = "") -> list[dict]:
    """添加股票到自选列表（按代码去重）.

    Args:
        data_dir: 数据目录.
        code: 6 位股票代码.
        name: 股票名称，可为空串（显示层用行情数据补齐）.

    Returns:
        更新后的完整自选列表.

    Raises:
        ValueError: code 不是 6 位数字.
    """
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("代码须为 6 位数字")
    with _lock:
        items = load_watchlist(data_dir)
        if not any(i.get("code") == code for i in items):
            items.append({"code": code, "name": name})
        _write(data_dir, items)
        return items


def remove_watchlist(data_dir: Path, code: str) -> list[dict]:
    """从自选列表删除股票.

    Args:
        data_dir: 数据目录.
        code: 6 位股票代码.

    Returns:
        更新后的完整自选列表.
    """
    with _lock:
        items = [i for i in load_watchlist(data_dir) if i.get("code") != code]
        _write(data_dir, items)
        return items


def _write(data_dir: Path, items: list[dict]) -> None:
    """原子写入自选列表（先写临时文件再替换，避免半写损坏）.

    Args:
        data_dir: 数据目录.
        items: 待写入的列表.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    p = _path(data_dir)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
