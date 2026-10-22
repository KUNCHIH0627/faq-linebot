"""匯入範例課程與 FAQ：  python -m app.seed
已經有資料就不會重複匯入。標示「（範例）」的內容是示意用的，請改成你們課程的真實資訊。

關鍵字 weight 的設計：專有名詞給 3（單獨命中就達門檻、直接回答），
泛用詞給 1～2（例如只問「作業」只會列出建議，問「作業怎麼繳交」才會直接回答）。
"""
from sqlalchemy.orm import Session

from . import models  # noqa: F401  讓所有資料表定義被載入
from .core.database import Base, SessionLocal, engine
from .models.faq import Course, Faq
from .services.faqs import save_faq

# （範例）課程代碼請改成實際課號
COURSES = [
    ("DB", "資料庫系統"),
    ("WEB", "網頁程式設計"),
]

# (課程代碼們, 類別, 問題, 答案, [(關鍵字, weight), ...])
SAMPLES = [
    # ---- 資料庫系統 ----
    (["DB"], "SQL", "什麼是 JOIN？", "JOIN 用來把兩張以上的資料表，依照共同欄位（例如外鍵）合併成一張查詢結果。INNER JOIN 只保留兩邊都對得上的資料；LEFT JOIN 會保留左表全部資料，右表對不上的欄位填 NULL。",
     [("join", 3), ("連接", 2), ("inner join", 3), ("left join", 3), ("合併資料表", 3)]),
    (["DB"], "SQL", "PRIMARY KEY 和 FOREIGN KEY 差在哪？", "PRIMARY KEY（主鍵）用來唯一識別一張表中的每一筆資料，不能重複也不能是 NULL。FOREIGN KEY（外鍵）是指向另一張表主鍵的欄位，用來建立兩張表之間的關聯並維持參照完整性。",
     [("主鍵", 3), ("外鍵", 3), ("primary key", 3), ("foreign key", 3), ("pk", 2), ("fk", 2)]),
    (["DB"], "SQL", "WHERE 和 HAVING 有什麼不同？", "WHERE 在分組之前先過濾每一筆資料；HAVING 在 GROUP BY 分組之後，過濾整個群組（通常搭配 COUNT、SUM 等聚合函數）。",
     [("where", 3), ("having", 3), ("group by", 2), ("分組", 2), ("聚合", 2)]),
    (["DB"], "正規化", "什麼是正規化？為什麼要做？", "正規化是把資料表拆分成結構更合理的多張表，減少重複資料與更新異常（新增、修改、刪除時的不一致）。常見到第三正規化（3NF）。",
     [("正規化", 3), ("normalization", 3), ("1nf", 3), ("2nf", 3), ("3nf", 3), ("異常", 1)]),
    (["DB"], "考試", "資料庫系統的考試範圍是什麼？", "（範例）請以老師公告的範圍為準。請改成實際的考試範圍與日期。",
     [("考試", 3), ("期中", 3), ("期末", 3), ("範圍", 1), ("考古題", 3)]),
    # ---- 兩門課共用（多對多的例子）----
    (["DB", "WEB"], "作業", "作業要怎麼繳交？", "（範例）請以各課程公告為準，通常是將程式推到 GitHub 並在指定平台繳交連結。請改成實際的繳交方式與期限。",
     [("作業", 2), ("繳交", 2), ("交作業", 3), ("deadline", 2), ("期限", 1)]),
    # ---- 網頁程式設計 ----
    (["WEB"], "HTML/CSS", "HTML、CSS、JavaScript 各自負責什麼？", "HTML 負責網頁的結構與內容；CSS 負責外觀樣式（顏色、版面、字型）；JavaScript 負責互動與行為（點擊、動態更新資料）。",
     [("html", 3), ("css", 3), ("javascript", 3), ("js", 2), ("前端", 2), ("三個差別", 1)]),
    (["WEB"], "API", "什麼是 API？", "API 是程式之間溝通的介面。例如前端網頁用 HTTP 向後端送出請求（GET 取得、POST 新增、PUT 修改、DELETE 刪除），後端回傳 JSON 資料。",
     [("api", 3), ("介面", 2), ("http", 2), ("get", 1), ("post", 1), ("restful", 3), ("rest", 2)]),
    (["WEB"], "API", "FastAPI 的 API 文件在哪裡看？", "啟動伺服器後，打開網址結尾的 /api/docs 就是自動產生的 Swagger 文件，可以直接在上面測試每個 API。",
     [("fastapi", 3), ("swagger", 3), ("docs", 3), ("文件", 2), ("openapi", 3)]),
    (["WEB"], "工具", "怎麼把程式推到 GitHub？", "常用指令：git add .（加入變更）→ git commit -m \"說明\"（提交）→ git push（推到遠端）。第一次要先用 git remote add origin 網址 設定遠端。",
     [("github", 3), ("git", 3), ("push", 2), ("commit", 2), ("推", 1), ("版本控制", 3)]),
]


def seed(db: Session) -> int:
    """寫入範例課程與 FAQ 並 commit，回傳匯入的 FAQ 筆數。"""
    for code, name in COURSES:
        db.add(Course(code=code, name=name))
    db.flush()
    for codes, category, q, a, kws in SAMPLES:
        save_faq(db, Faq(), category=category, question=q, answer=a, course_codes=codes, keywords=kws)
    db.commit()
    return len(SAMPLES)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Faq).count() > 0 or db.query(Course).count() > 0:
            print("已經有課程或 FAQ 資料，略過匯入。")
            return
        n = seed(db)
        print(f"已匯入 {len(COURSES)} 門課程、{n} 筆範例 FAQ。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
