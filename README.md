# 課程 FAQ LINE Bot

LINE 當介面 → FastAPI 後端 → 資料庫存 FAQ。使用者在 LINE 問問題，後端比對 FAQ 回答，並把每次提問記下來，統計「常見問題排行榜」與「沒答到的問題」。

```
使用者 ──LINE──▶ LINE 伺服器 ──POST /api/webhook──▶ FastAPI ──▶ 資料庫 (faq / question_log)
                                                      │
                                      Reply API ◀─────┘ 比對 FAQ，回覆答案
```

## 1. 在自己的電腦跑起來（Windows）

```bat
cd api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

打開 `api\.env`：
- `DATABASE_URL`：填你的 PostgreSQL。**留空或刪掉這行**會自動用本機 `faq.db`（SQLite），可以先不裝資料庫就測試。
- `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN`：到 LINE Developers → 你的 **Messaging API channel**，分別在 *Basic settings*（Channel secret）和 *Messaging API*（Channel access token，按 Issue）。
- `ROOT_PATH`：用學校轉發時填 `/s113321002`，本機測試留空。

```bat
python -m app.seed          :: 匯入範例 FAQ（只會匯入一次）
run.bat                     :: 啟動，埠號 7777
```

打開 http://localhost:7777/api/docs 看 Swagger。FAQ 內容就在這裡的 `/api/faqs` 新增、修改、刪除。

## 2. 接上 LINE

Webhook URL 要是公開的 HTTPS：
- 學校轉發：`https://demo.wke.csie.ncnu.edu.tw/s113321002/api/webhook`
- 或用 ngrok / Cloudflare Tunnel：`https://你的網域/api/webhook`

LINE Developers → Messaging API → Webhook URL 填上，按 **Verify** 看到 Success，再打開 **Use webhook**。
Official Account Manager → 回應設定：**關閉「自動回應訊息」**，Webhook 保持開啟。

## 3. API 一覽

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/api/webhook` | LINE 送訊息來的入口（驗證簽章） |
| GET/POST | `/api/faqs` | 列出 / 新增 FAQ（可用 `?course=` 篩選） |
| GET/PUT/DELETE | `/api/faqs/{id}` | 查詢 / 修改 / 刪除 |
| GET | `/api/analytics/top-faqs` | 常見問題排行榜 |
| GET | `/api/analytics/unanswered` | 沒答到的問題（下一批該補的 FAQ） |

## 4. 資料表

- `faq(id, course, category, question, answer, keywords, created_at)`
- `question_log(id, line_user_id, question_text, faq_id → faq.id, matched, created_at)`

## 5. 比對邏輯（`app/services/matcher.py`）

關鍵字命中每個 +3；問句與 FAQ 問題互相包含 +5；字面相似度 ×3。最高分 ≥ 3 就回答，1.5～3 的當作「你是不是想問」。簡單好解釋，之後可以換成向量檢索（RAG）而不用動其他程式。

## 6. 測試

```bat
cd api
pytest
```
