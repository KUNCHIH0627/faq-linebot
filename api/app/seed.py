"""匯入範例 FAQ：  python -m app.seed
已經有資料就不會重複匯入。標示「（範例）」的答案是示意用的，請改成你們課程的真實資訊。"""
from .core.database import Base, SessionLocal, engine
from .models.faq import Faq

SAMPLES = [
    # ---- 資料庫系統 ----
    ("資料庫系統", "SQL", "什麼是 JOIN？", "JOIN 用來把兩張以上的資料表，依照共同欄位（例如外鍵）合併成一張查詢結果。INNER JOIN 只保留兩邊都對得上的資料；LEFT JOIN 會保留左表全部資料，右表對不上的欄位填 NULL。", "join,連接,inner join,left join,合併資料表"),
    ("資料庫系統", "SQL", "PRIMARY KEY 和 FOREIGN KEY 差在哪？", "PRIMARY KEY（主鍵）用來唯一識別一張表中的每一筆資料，不能重複也不能是 NULL。FOREIGN KEY（外鍵）是指向另一張表主鍵的欄位，用來建立兩張表之間的關聯並維持參照完整性。", "主鍵,外鍵,primary key,foreign key,pk,fk"),
    ("資料庫系統", "SQL", "WHERE 和 HAVING 有什麼不同？", "WHERE 在分組之前先過濾每一筆資料；HAVING 在 GROUP BY 分組之後，過濾整個群組（通常搭配 COUNT、SUM 等聚合函數）。", "where,having,group by,分組,聚合"),
    ("資料庫系統", "正規化", "什麼是正規化？為什麼要做？", "正規化是把資料表拆分成結構更合理的多張表，減少重複資料與更新異常（新增、修改、刪除時的不一致）。常見到第三正規化（3NF）。", "正規化,normalization,1nf,2nf,3nf,異常"),
    ("資料庫系統", "作業", "資料庫系統的作業要怎麼繳交？", "（範例）請以課程公告為準，通常是將程式推到 GitHub 並在指定平台繳交連結。請改成實際的繳交方式。", "作業,繳交,交作業,deadline,期限"),
    ("資料庫系統", "考試", "資料庫系統的考試範圍是什麼？", "（範例）請以老師公告的範圍為準。請改成實際的考試範圍與日期。", "考試,期中,期末,範圍,考古題"),
    # ---- 網頁程式設計 ----
    ("網頁程式設計", "HTML/CSS", "HTML、CSS、JavaScript 各自負責什麼？", "HTML 負責網頁的結構與內容；CSS 負責外觀樣式（顏色、版面、字型）；JavaScript 負責互動與行為（點擊、動態更新資料）。", "html,css,javascript,js,前端,三個差別"),
    ("網頁程式設計", "API", "什麼是 API？", "API 是程式之間溝通的介面。例如前端網頁用 HTTP 向後端送出請求（GET 取得、POST 新增、PUT 修改、DELETE 刪除），後端回傳 JSON 資料。", "api,介面,http,get,post,restful,rest"),
    ("網頁程式設計", "API", "FastAPI 的 API 文件在哪裡看？", "啟動伺服器後，打開網址結尾的 /api/docs 就是自動產生的 Swagger 文件，可以直接在上面測試每個 API。", "fastapi,swagger,docs,文件,openapi"),
    ("網頁程式設計", "作業", "網頁程式設計的作業要怎麼繳交？", "（範例）請以課程公告為準。請改成實際的繳交方式與期限。", "作業,繳交,交作業,deadline,期限"),
    ("網頁程式設計", "工具", "怎麼把程式推到 GitHub？", "常用指令：git add .（加入變更）→ git commit -m \"說明\"（提交）→ git push（推到遠端）。第一次要先用 git remote add origin 網址 設定遠端。", "github,git,push,commit,推,版本控制"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Faq).count() > 0:
            print("faq 資料表已經有資料，略過匯入。")
            return
        for course, category, q, a, kw in SAMPLES:
            db.add(Faq(course=course, category=category, question=q, answer=a, keywords=kw))
        db.commit()
        print(f"已匯入 {len(SAMPLES)} 筆範例 FAQ。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
