"""本地自选列表存储/API 的单元测试."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import watchlist


def test_watchlist_empty(tmp_path: Path):
    """目录无文件时返回空列表."""
    assert watchlist.load_watchlist(tmp_path) == []


def test_watchlist_add_and_remove(tmp_path: Path):
    """添加去重与删除."""
    watchlist.add_watchlist(tmp_path, "600519", "贵州茅台")
    watchlist.add_watchlist(tmp_path, "000001", "平安银行")
    assert len(watchlist.load_watchlist(tmp_path)) == 2
    # 去重
    watchlist.add_watchlist(tmp_path, "600519")
    assert len(watchlist.load_watchlist(tmp_path)) == 2
    watchlist.remove_watchlist(tmp_path, "600519")
    assert [i["code"] for i in watchlist.load_watchlist(tmp_path)] == ["000001"]


def test_watchlist_bad_code(tmp_path: Path):
    """非法代码抛 ValueError."""
    with pytest.raises(ValueError):
        watchlist.add_watchlist(tmp_path, "abc")


def test_watchlist_corrupt_file(tmp_path: Path):
    """损坏文件降级为空列表并备份."""
    (tmp_path / "watchlist.json").write_text("{not json", encoding="utf-8")
    assert watchlist.load_watchlist(tmp_path) == []
    assert (tmp_path / "watchlist.json.bak").exists()


def test_watchlist_api(tmp_path: Path, monkeypatch):
    """/api/watchlist 增删查."""
    from app.config import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    from app.main import app
    # 直接调用（不进 context manager），避免触发 lifespan 启动调度器连真实网络
    client = TestClient(app)
    assert client.get("/api/watchlist").json() == []
    r = client.post("/api/watchlist", json={"code": "600519"})
    assert r.status_code == 200
    assert [i["code"] for i in r.json()] == ["600519"]
    r = client.post("/api/watchlist", json={"code": "bad"})
    assert r.status_code == 400
    r = client.delete("/api/watchlist/600519")
    assert r.json() == []
