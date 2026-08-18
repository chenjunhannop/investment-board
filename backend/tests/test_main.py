# backend/tests/test_main.py
def test_app_importable():
    from app.main import app
    assert app.title == "Investment Board"


def test_default_port():
    import os
    os.environ.pop("IB_PORT", None)
    from app.config import settings
    assert settings.port == 8210
