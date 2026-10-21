import os
from pathlib import Path

from dotenv import load_dotenv

# 先載入 .env，確保 ROOT_PATH 等變數在建立 app 之前就緒
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI

from . import models  # noqa: F401  讓資料表定義被載入
from .api import router as api_router
from .core.database import Base, engine

# 啟動時自動建立不存在的資料表（已存在的不會動）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="課程 FAQ LINE Bot",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    root_path=os.getenv("ROOT_PATH", ""),  # 放在學校反向代理後面時，Swagger 才找得到 openapi.json
)

app.include_router(api_router, prefix="/api")


@app.get("/", include_in_schema=False)
def index():
    return {"service": "course-faq-linebot", "docs": "api/docs"}
