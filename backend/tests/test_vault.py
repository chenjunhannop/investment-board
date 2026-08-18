"""Vault 会话存储的单元测试：加解密往返、密文不可读与清除/缺失行为."""
from pathlib import Path

from app.vault.store import Vault


def _make_vault(tmp_path: Path, monkeypatch):
    """注入固定密钥的假 keyring，避免测试触碰系统 Keychain."""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    monkeypatch.setattr("app.vault.store._keyring_get", lambda service, user: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda service, user, pw: None)
    return Vault(tmp_path)


def test_save_load_roundtrip(tmp_path, monkeypatch):
    """保存会话后能原样读回."""
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc", "user": "u1"})
    loaded = v.load_session()
    assert loaded == {"token": "abc", "user": "u1"}


def test_ciphertext_not_plaintext(tmp_path, monkeypatch):
    """落盘文件不应包含明文会话值."""
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "secret-value"})
    raw = (tmp_path / "session.enc").read_bytes()
    assert b"secret-value" not in raw


def test_clear_removes_session(tmp_path, monkeypatch):
    """清除后登出态且无法读回会话."""
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc"})
    v.clear()
    assert not v.is_logged_in
    assert v.load_session() is None


def test_load_none_when_missing(tmp_path, monkeypatch):
    """无会话文件时 load_session 返回 None."""
    v = _make_vault(tmp_path, monkeypatch)
    assert v.load_session() is None
