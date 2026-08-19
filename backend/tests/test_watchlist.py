"""本地自选列表（分组结构）存储的单元测试."""
from pathlib import Path

import pytest

from app.core import watchlist


def test_empty(tmp_path: Path):
    """目录无文件时返回空分组结构."""
    assert watchlist.load_watchlist(tmp_path) == {"version": 2, "groups": []}


def test_group_crud(tmp_path: Path):
    """文件夹新建/重命名/删除."""
    watchlist.add_group(tmp_path, "银行")
    watchlist.add_group(tmp_path, "白酒")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["银行", "白酒"]
    with pytest.raises(ValueError):
        watchlist.add_group(tmp_path, "银行")  # 重名
    watchlist.rename_group(tmp_path, "银行", "银行股")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["银行股", "白酒"]
    watchlist.remove_group(tmp_path, "银行股")
    assert [g["name"] for g in watchlist.load_watchlist(tmp_path)["groups"]] == ["白酒"]


def test_stock_crud(tmp_path: Path):
    """向文件夹添加/删除股票，去重."""
    watchlist.add_group(tmp_path, "白酒")
    watchlist.add_stock(tmp_path, "白酒", "600519")
    watchlist.add_stock(tmp_path, "白酒", "000858")
    watchlist.add_stock(tmp_path, "白酒", "600519")  # 去重
    stocks = watchlist.load_watchlist(tmp_path)["groups"][0]["stocks"]
    assert [s["code"] for s in stocks] == ["600519", "000858"]
    watchlist.remove_stock(tmp_path, "白酒", "600519")
    assert [s["code"] for s in watchlist.load_watchlist(tmp_path)["groups"][0]["stocks"]] == ["000858"]


def test_stock_validation(tmp_path: Path):
    """非法代码与不存在的文件夹/股票抛 ValueError."""
    watchlist.add_group(tmp_path, "A")
    with pytest.raises(ValueError):
        watchlist.add_stock(tmp_path, "A", "abc")
    with pytest.raises(ValueError):
        watchlist.add_stock(tmp_path, "不存在", "600519")
    watchlist.add_stock(tmp_path, "A", "600519")
    with pytest.raises(ValueError):
        watchlist.remove_stock(tmp_path, "A", "000000")


def test_v1_migration(tmp_path: Path):
    """v1 扁平数组自动迁移到未分组文件夹."""
    (tmp_path / "watchlist.json").write_text(
        '[{"code": "600519", "name": ""}]', encoding="utf-8")
    data = watchlist.load_watchlist(tmp_path)
    assert data["version"] == 2
    assert data["groups"][0]["name"] == "未分组"
    assert data["groups"][0]["stocks"][0]["code"] == "600519"


def test_collect_codes(tmp_path: Path):
    """collect_codes 遍历所有文件夹."""
    watchlist.add_group(tmp_path, "A")
    watchlist.add_group(tmp_path, "B")
    watchlist.add_stock(tmp_path, "A", "600519")
    watchlist.add_stock(tmp_path, "B", "000001")
    watchlist.add_stock(tmp_path, "B", "600519")
    assert watchlist.collect_codes(tmp_path) == ["000001", "600519"]


def test_corrupt_file(tmp_path: Path):
    """损坏文件降级为空结构并备份."""
    (tmp_path / "watchlist.json").write_text("{bad", encoding="utf-8")
    assert watchlist.load_watchlist(tmp_path) == {"version": 2, "groups": []}
    assert (tmp_path / "watchlist.json.bak").exists()
