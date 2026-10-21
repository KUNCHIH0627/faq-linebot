import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.faq import Faq, QuestionLog
from ..schemas.faq import FaqCreate, FaqResponse
from ..services import line
from ..services.bot import handle_text

logger = logging.getLogger("routes")
router = APIRouter()


@router.get("/ping", tags=["system"])
def ping():
    return {"message": "pong"}


# ---------------- LINE webhook ----------------

@router.post("/webhook", tags=["line"])
async def line_webhook(
    request: Request,
    x_line_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not line.get_secret():
        raise HTTPException(status_code=500, detail="伺服器沒有設定 LINE_CHANNEL_SECRET")

    body = await request.body()  # 簽章要對「原始 body」驗證，所以不能先轉成 JSON
    if not line.verify_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="簽章錯誤")

    try:
        events = json.loads(body).get("events", [])
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="body 不是合法的 JSON")

    for event in events:  # LINE 按 Verify 時 events 是空的，直接回 200 即可
        if event.get("type") != "message" or event.get("message", {}).get("type") != "text":
            continue
        user_id = event.get("source", {}).get("userId")
        reply = handle_text(db, user_id, event["message"]["text"])
        await line.reply_text(event["replyToken"], reply)

    return {"status": "ok"}


# ---------------- FAQ CRUD ----------------

@router.post("/faqs", response_model=FaqResponse, status_code=201, tags=["faq"])
def create_faq(data: FaqCreate, db: Session = Depends(get_db)):
    faq = Faq(**data.model_dump())
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return faq


@router.get("/faqs", response_model=list[FaqResponse], tags=["faq"])
def list_faqs(course: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Faq)
    if course:
        q = q.filter(Faq.course == course)
    return q.order_by(Faq.id).all()


@router.get("/faqs/{faq_id}", response_model=FaqResponse, tags=["faq"])
def get_faq(faq_id: int, db: Session = Depends(get_db)):
    faq = db.get(Faq, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq


@router.put("/faqs/{faq_id}", response_model=FaqResponse, tags=["faq"])
def update_faq(faq_id: int, data: FaqCreate, db: Session = Depends(get_db)):
    faq = db.get(Faq, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    for key, value in data.model_dump().items():
        setattr(faq, key, value)
    db.commit()
    db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}", status_code=204, tags=["faq"])
def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    faq = db.get(Faq, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    db.delete(faq)
    db.commit()


# ---------------- 常見問題排行榜 ----------------

@router.get("/analytics/top-faqs", tags=["analytics"])
def top_faqs(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """被問最多次的 FAQ（只算有命中的）。"""
    rows = (
        db.query(Faq.id, Faq.course, Faq.question, func.count(QuestionLog.id).label("cnt"))
        .join(QuestionLog, QuestionLog.faq_id == Faq.id)
        .group_by(Faq.id, Faq.course, Faq.question)
        .order_by(func.count(QuestionLog.id).desc(), Faq.id)
        .limit(limit)
        .all()
    )
    return [
        {"rank": i + 1, "faq_id": r.id, "course": r.course, "question": r.question, "count": r.cnt}
        for i, r in enumerate(rows)
    ]


@router.get("/analytics/unanswered", tags=["analytics"])
def unanswered(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """沒找到答案的問題，依出現次數排序：這就是下一批該補進 FAQ 的題目。"""
    rows = (
        db.query(QuestionLog.question_text, func.count(QuestionLog.id).label("cnt"))
        .filter(QuestionLog.matched.is_(False))
        .group_by(QuestionLog.question_text)
        .order_by(func.count(QuestionLog.id).desc(), QuestionLog.question_text)
        .limit(limit)
        .all()
    )
    return [{"question": r.question_text, "count": r.cnt} for r in rows]
