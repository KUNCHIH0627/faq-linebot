"""建立專案專用的 PostgreSQL 資料庫：  python -m app.create_db
讀 .env 的 DATABASE_URL，連到系統內建的 postgres 資料庫，建立 URL 最後指定的那個新資料庫。"""
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from .core.database import DATABASE_URL


def main() -> None:
    if not DATABASE_URL.startswith("postgresql"):
        print("DATABASE_URL 不是 PostgreSQL，不需要建立資料庫。")
        return

    info = conninfo_to_dict(DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1))
    target = info.get("dbname")
    if not target:
        print("DATABASE_URL 最後面沒有資料庫名稱。")
        return

    info["dbname"] = "postgres"
    with psycopg.connect(make_conninfo(**info), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,)).fetchone()
        if exists:
            print(f"資料庫 {target} 已經存在。")
        else:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
            print(f"已建立資料庫 {target}。")


if __name__ == "__main__":
    main()