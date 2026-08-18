# backend/tests/test_vault.py
from pathlib import Path

from app.vault.store import Vault


def _make_vault(tmp_path: Path, monkeypatch):
    """注入固定密钥的假 keyring，避免测试触碰系统 Keychain。"""
    monkeypatch.setenv("IB_TEST_KEYCHAIN", "1")
    monkeypatch.setattr("app.vault.store._keyring_get", lambda service, user: "0" * 44)
    monkeypatch.setattr("app.vault.store._keyring_set", lambda service, user, pw: None)
    return Vault(tmp_path)


def test_save_load_roundtrip(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc", "user": "u1"})
    loaded = v.load_session()
    assert loaded == {"token": "abc", "user": "u1"}


def test_ciphertext_not_plaintext(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "secret-value"})
    raw = (tmp_path / "session.enc").read_bytes()
    assert b"secret-value" not in raw


def test_clear_removes_session(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    v.save_session({"token": "abc"})
    v.clear()
    assert not v.is_logged_in
    assert v.load_session() is None


def test_load_none_when_missing(tmp_path, monkeypatch):
    v = _make_vault(tmp_path, monkeypatch)
    assert v.load_session() is None
