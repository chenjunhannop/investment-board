"""会话凭据的安全存储.

使用 AES-256-GCM 加密会话载荷并落盘到 data_dir/session.enc，文件头为
``v1`` 魔数（2 字节）+ 12 字节随机 nonce + 密文；加密密钥保存在系统钥匙串
（keyring），测试环境通过环境变量 IB_TEST_KEYCHAIN 使用固定密钥.
"""
import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SERVICE = "investment-board"
_KEYCHAIN_USER = "session"


def _keyring_get(service: str, user: str) -> str | None:
    """从系统钥匙串读取密码.

    Args:
        service: 钥匙串服务名.
        user: 钥匙串账户名.

    Returns:
        存储的密码字符串；不存在时返回 None.
    """
    import keyring
    return keyring.get_password(service, user)


def _keyring_set(service: str, user: str, password: str) -> None:
    """把密码写入系统钥匙串.

    Args:
        service: 钥匙串服务名.
        user: 钥匙串账户名.
        password: 要写入的密码字符串.
    """
    import keyring
    keyring.set_password(service, user, password)


def _get_or_create_key() -> bytes:
    """获取加密密钥，不存在则生成并存入钥匙串.

    测试分支：当环境变量 IB_TEST_KEYCHAIN 被设置时，直接返回固定全零密钥，
    避免在 CI/测试环境依赖真实钥匙串.

    Returns:
        32 字节 AES-256 密钥.
    """
    if os.environ.get("IB_TEST_KEYCHAIN"):
        return bytes.fromhex("00" * 32)  # 测试用固定密钥
    existing = _keyring_get(_SERVICE, _KEYCHAIN_USER)
    if existing:
        return base64.b64decode(existing)
    key = os.urandom(32)
    _keyring_set(_SERVICE, _KEYCHAIN_USER, base64.b64encode(key).decode())
    return key


class Vault:
    """AES-256-GCM 加密的会话凭据存储（v1 头格式：``v1`` + nonce + 密文）."""

    def __init__(self, data_dir: Path):
        """初始化会话存储目录.

        Args:
            data_dir: 存放加密会话文件的目录，不存在会自动创建.
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.data_dir / "session.enc"

    def save_session(self, payload: dict[str, Any]) -> None:
        """加密并落盘会话载荷.

        Args:
            payload: 会话字段字典（如 token、user）.
        """
        key = _get_or_create_key()
        nonce = os.urandom(12)
        raw = json.dumps(payload, ensure_ascii=False).encode()
        ct = AESGCM(key).encrypt(nonce, raw, None)
        self._file.write_bytes(b"v1" + nonce + ct)

    def load_session(self) -> dict[str, Any] | None:
        """解密并读取已保存的会话.

        Returns:
            会话字段字典；文件不存在时返回 None.

        Raises:
            AssertionError: 文件头不是 ``v1`` 魔数时抛出.
        """
        if not self._file.exists():
            return None
        blob = self._file.read_bytes()
        assert blob[:2] == b"v1"
        key = _get_or_create_key()
        nonce, ct = blob[2:14], blob[14:]
        raw = AESGCM(key).decrypt(nonce, ct, None)
        data = json.loads(raw.decode())
        return data if isinstance(data, dict) else None

    def clear(self) -> None:
        """删除已保存的加密会话文件."""
        self._file.unlink(missing_ok=True)

    @property
    def is_logged_in(self) -> bool:
        """是否存在已保存的加密会话文件."""
        return self._file.exists()
