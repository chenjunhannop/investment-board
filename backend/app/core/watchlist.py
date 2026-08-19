"""本地自选股列表（文件夹分组）的加载/增删（JSON 持久化，含并发锁与原子写）.

v2 结构: {"version": 2, "groups": [{"name": str, "stocks": [{"code","name"}]}]}
"""
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


def _empty() -> dict:
    """返回空分组结构.

    Returns:
        {"version": 2, "groups": []}.
    """
    return {"version": 2, "groups": []}


def _read(data_dir: Path) -> dict:
    """读取文件并做 v1→v2 迁移；损坏或不存在时返回空结构."""
    p = _path(data_dir)
    if not p.exists():
        return _empty()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # v1 扁平 [{code,name}] → v2，迁移到"未分组"文件夹
            stocks = [i for i in data if isinstance(i, dict) and i.get("code")]
            migrated = {"version": 2, "groups": [{"name": "未分组", "stocks": stocks}]}
            _write(data_dir, migrated)
            return migrated
        if isinstance(data, dict) and isinstance(data.get("groups"), list):
            return data
        return _empty()
    except (json.JSONDecodeError, OSError):
        try:
            p.rename(p.with_suffix(".json.bak"))
        except OSError:
            pass
        return _empty()


def _write(data_dir: Path, data: dict) -> None:
    """原子写入自选列表（先写临时文件再替换，避免半写损坏）.

    Args:
        data_dir: 数据目录.
        data: v2 分组结构字典.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    p = _path(data_dir)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def load_watchlist(data_dir: Path) -> dict:
    """读取本地自选列表.

    Args:
        data_dir: 数据目录.

    Returns:
        v2 分组结构 {"version": 2, "groups": [...]}.
    """
    with _lock:
        return _read(data_dir)


def add_group(data_dir: Path, name: str) -> dict:
    """新建空文件夹.

    Args:
        data_dir: 数据目录.
        name: 文件夹名（非空）.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 名称为空或与已有文件夹重名.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("文件夹名不能为空")
    with _lock:
        data = _read(data_dir)
        if any(g["name"] == name for g in data["groups"]):
            raise ValueError("文件夹已存在")
        data["groups"].append({"name": name, "stocks": []})
        _write(data_dir, data)
        return data


def rename_group(data_dir: Path, name: str, new_name: str) -> dict:
    """重命名文件夹.

    Args:
        data_dir: 数据目录.
        name: 当前文件夹名.
        new_name: 新文件夹名（非空）.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹不存在或新名称与其它文件夹重名.
    """
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValueError("文件夹名不能为空")
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == name), None)
        if target is None:
            raise ValueError("文件夹不存在")
        if any(g["name"] == new_name and g is not target for g in groups):
            raise ValueError("文件夹已存在")
        target["name"] = new_name
        _write(data_dir, data)
        return data


def remove_group(data_dir: Path, name: str) -> dict:
    """删除文件夹（连带删除其中全部股票）.

    Args:
        data_dir: 数据目录.
        name: 文件夹名.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹不存在.
    """
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        if not any(g["name"] == name for g in groups):
            raise ValueError("文件夹不存在")
        data["groups"] = [g for g in groups if g["name"] != name]
        _write(data_dir, data)
        return data


def add_stock(data_dir: Path, group: str, code: str) -> dict:
    """向指定文件夹添加股票（按代码去重）.

    Args:
        data_dir: 数据目录.
        group: 目标文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 代码非法或文件夹不存在.
    """
    code = (code or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("代码须为 6 位数字")
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == group), None)
        if target is None:
            raise ValueError("文件夹不存在")
        if not any(s["code"] == code for s in target["stocks"]):
            target["stocks"].append({"code": code, "name": ""})
        _write(data_dir, data)
        return data


def remove_stock(data_dir: Path, group: str, code: str) -> dict:
    """从指定文件夹删除股票.

    Args:
        data_dir: 数据目录.
        group: 文件夹名.
        code: 6 位股票代码.

    Returns:
        更新后的分组结构.

    Raises:
        ValueError: 文件夹或股票不存在.
    """
    with _lock:
        data = _read(data_dir)
        groups = data["groups"]
        target = next((g for g in groups if g["name"] == group), None)
        if target is None:
            raise ValueError("文件夹不存在")
        before = len(target["stocks"])
        target["stocks"] = [s for s in target["stocks"] if s["code"] != code]
        if len(target["stocks"]) == before:
            raise ValueError("股票不存在")
        _write(data_dir, data)
        return data


def collect_codes(data_dir: Path) -> list[str]:
    """遍历所有文件夹收集股票代码并排序返回.

    Args:
        data_dir: 数据目录.

    Returns:
        全部文件夹内代码的排序去重列表.
    """
    codes = set()
    for g in _read(data_dir)["groups"]:
        for s in g["stocks"]:
            codes.add(s["code"])
    return sorted(codes)
