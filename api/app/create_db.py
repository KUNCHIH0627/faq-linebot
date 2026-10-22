"""建立資料庫與所有資料表：  python -m app.create_db
1. 如果 DATABASE_URL 是 PostgreSQL：連到系統內建的 postgres 資料庫，建立 URL 最後指定的那個新資料庫（已存在就略過）。
2. 不論 PostgreSQL 或 SQLite：建立所有還不存在的資料表（已存在的不會動）。

從舊版（faq + question_log）升級時，舊的 faq 表欄位不同，create_all 不會修改它，要用：
    python -m app.create_db --reset
先刪掉舊表與本專案所有資料表再重建。⚠️ 會清空所有資料，無法復原。"""
import argparse

from sqlalchemy import inspect, text

from . import models  # noqa: F401  讓所有資料表定義被載入
from .core.database import DATABASE_URL, Base, engine

LEGACY_TABLES = ["question_log"]  # 舊版才有、新版已經不用的表


def create_database() -> None:
    if not DATABASE_URL.startswith("postgresql"):
        print("DATABASE_URL 不是 PostgreSQL，不需要建立資料庫。")
        return

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    info = conninfo_to_dict(DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1))
    target = info.get("dbname")
    if not target:
        raise SystemExit("DATABASE_URL 最後面沒有資料庫名稱。")

    info["dbname"] = "postgres"
    with psycopg.connect(make_conninfo(**info), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,)).fetchone()
        if exists:
            print(f"資料庫 {target} 已經存在。")
        else:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
            print(f"已建立資料庫 {target}。")


def drop_all_tables() -> None:
    existing = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        for name in LEGACY_TABLES:
            if name in existing:
                conn.execute(text(f"DROP TABLE {name}"))
                print(f"已刪除舊表 {name}。")
    Base.metadata.drop_all(bind=engine)
    print("已刪除本專案所有資料表。")


def create_tables() -> None:
    before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine)
    for name in Base.metadata.sorted_tables:
        status = "已存在" if name.name in before else "已建立"
        print(f"  {status}：{name.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="建立資料庫與所有資料表")
    parser.add_argument("--reset", action="store_true", help="先刪除所有資料表再重建（會清空資料）")
    args = parser.parse_args()

    create_database()
    if args.reset:
        answer = input("⚠️ 這會刪除所有資料表與資料，無法復原。確定請輸入 yes：")
        if answer.strip().lower() != "yes":
            print("已取消。")
            return
        drop_all_tables()
    print("資料表：")
    create_tables()


if __name__ == "__main__":
    main()
