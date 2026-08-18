# backend/app/vault/store.py
import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SERVICE = "investment-board"
_KEYCHAIN_USER = "session"


def _keyring_get(service: str, user: str) -> str | None:
    import keyring
    return keyring.get_password(service, user)


def _keyring_set(service: str, user: str, password: str) -> None:
    import keyring
    keyring.set_password(service, user, password)


def _get_or_create_key() -> bytes:
    if os.environ.get("IB_TEST_KEYCHAIN"):
        return bytes.fromhex("00" * 32)  # 测试用固定密钥
    existing = _keyring_get(_SERVICE, _KEYCHAIN_USER)
    if existing:
        return base64.b64decode(existing)
    key = os.urandom(32)
    _keyring_set(_SERVICE, _KEYCHAIN_USER, base64.b64encode(key).decode())
    return key


class Vault:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.data_dir / "session.enc"

    def save_session(self, payload: dict) -> None:
        key = _get_or_create_key()
        nonce = os.urandom(12)
        raw = json.dumps(payload, ensure_ascii=False).encode()
        ct = AESGCM(key).encrypt(nonce, raw, None)
        self._file.write_bytes(b"v1" + nonce + ct)

    def load_session(self) -> dict | None:
        if not self._file.exists():
            return None
        blob = self._file.read_bytes()
        assert blob[:2] == b"v1"
        key = _get_or_create_key()
        nonce, ct = blob[2:14], blob[14:]
        raw = AESGCM(key).decrypt(nonce, ct, None)
        return json.loads(raw.decode())

    def clear(self) -> None:
        self._file.unlink(missing_ok=True)

    @property
    def is_logged_in(self) -> bool:
        return self._file.exists()
