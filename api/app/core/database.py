import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# 讀取 api/.env
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# 沒設定 DATABASE_URL 時退回 SQLite，讓你不用先裝 PostgreSQL 也能跑起來
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./faq.db"

# SQLAlchemy 2.x 的 postgresql:// 預設找 psycopg2，但我們裝的是 psycopg（v3），要明確指定
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite"):
    # SQLite 預設不檢查外鍵，要每條連線自己打開，ON DELETE CASCADE 才會生效
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """每個請求給一個獨立的 Session，用完自動關閉。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
