import base64
import hashlib
import hmac
import os

# 測試用：獨立的 SQLite、假的 LINE 金鑰（要在 import app 之前設定）
os.environ["DATABASE_URL"] = "sqlite:///./test_faq.db"
os.environ["LINE_CHANNEL_SECRET"] = "test-secret"
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "test-token"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed
from app.services import line


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed(db)
    db.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sent(monkeypatch):
    """攔截要送給 LINE 的回覆，改成存到清單裡。"""
    box = []

    async def fake_reply(reply_token, text):
        box.append((reply_token, text))

    monkeypatch.setattr(line, "reply_text", fake_reply)
    return box


def sign(body: bytes, secret: str = "test-secret") -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
