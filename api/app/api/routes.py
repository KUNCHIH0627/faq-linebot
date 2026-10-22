import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.faq import Chat, ChatFaq, Course, Faq
from ..schemas.faq import CourseResponse, FaqCreate, FaqResponse
from ..services import line
from ..services.bot import handle_text
from ..services.faqs import UnknownCourseError, save_faq

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


# ---------------- 課程 ----------------

@router.get("/courses", response_model=list[CourseResponse], tags=["faq"])
def list_courses(db: Session = Depends(get_db)):
    return [CourseResponse(code=c.code, name=c.name) for c in db.query(Course).order_by(Course.course_id)]


# ---------------- FAQ CRUD ----------------

def to_response(faq: Faq) -> FaqResponse:
    return FaqResponse(
        faq_id=faq.faq_id,
        category=faq.category.name,
        question=faq.question,
        answer=faq.answer,
        is_active=faq.is_active,
        courses=[CourseResponse(code=c.code, name=c.name) for c in faq.courses],
        keywords=[{"word": link.keyword.word, "weight": link.weight} for link in faq.keyword_links],
        since=faq.since,
    )


def write_faq(db: Session, faq: Faq, data: FaqCreate) -> Faq:
    try:
        save_faq(
            db,
            faq,
            category=data.category,
            question=data.question,
            answer=data.answer,
            is_active=data.is_active,
            course_codes=data.course_codes,
            keywords=[(k.word, k.weight) for k in data.keywords],
        )
    except UnknownCourseError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(faq)
    return faq


def get_faq_or_404(db: Session, faq_id: int) -> Faq:
    faq = db.get(Faq, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq


@router.post("/faqs", response_model=FaqResponse, status_code=201, tags=["faq"])
def create_faq(data: FaqCreate, db: Session = Depends(get_db)):
    return to_response(write_faq(db, Faq(), data))


@router.get("/faqs", response_model=list[FaqResponse], tags=["faq"])
def list_faqs(course: str | None = None, db: Session = Depends(get_db)):
    """course 填課程代碼（例如 DB），會列出掛在這門課底下的所有 FAQ。"""
    q = db.query(Faq)
    if course:
        q = q.filter(Faq.courses.any(Course.code == course))
    return [to_response(f) for f in q.order_by(Faq.faq_id).all()]


@router.get("/faqs/{faq_id}", response_model=FaqResponse, tags=["faq"])
def get_faq(faq_id: int, db: Session = Depends(get_db)):
    return to_response(get_faq_or_404(db, faq_id))


@router.put("/faqs/{faq_id}", response_model=FaqResponse, tags=["faq"])
def update_faq(faq_id: int, data: FaqCreate, db: Session = Depends(get_db)):
    return to_response(write_faq(db, get_faq_or_404(db, faq_id), data))


@router.delete("/faqs/{faq_id}", status_code=204, tags=["faq"])
def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    """真的刪除（連同 faq_course、faq_keyword、chat_faq）。想保留統計就改用 PUT 把 is_active 設成 false。"""
    db.delete(get_faq_or_404(db, faq_id))
    db.commit()


# ---------------- 常見問題排行榜 ----------------

@router.get("/analytics/top-faqs", tags=["analytics"])
def top_faqs(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """被當成最終答案（chat_faq.rank = 1）最多次的 FAQ。"""
    cnt = func.count(ChatFaq.chat_id)
    rows = (
        db.query(Faq, cnt.label("cnt"))
        .join(ChatFaq, ChatFaq.faq_id == Faq.faq_id)
        .filter(ChatFaq.rank == 1)
        .group_by(Faq.faq_id)
        .order_by(cnt.desc(), Faq.faq_id)
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "faq_id": faq.faq_id,
            "question": faq.question,
            "courses": [c.name for c in faq.courses],
            "count": n,
        }
        for i, (faq, n) in enumerate(rows)
    ]


@router.get("/analytics/unanswered", tags=["analytics"])
def unanswered(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """沒有任何 chat_faq 紀錄的提問（沒答出來），依出現次數排序：這就是下一批該補進 FAQ 的題目。"""
    cnt = func.count(Chat.chat_id)
    rows = (
        db.query(Chat.question_text, cnt.label("cnt"))
        .filter(~exists().where(ChatFaq.chat_id == Chat.chat_id))
        .group_by(Chat.question_text)
        .order_by(cnt.desc(), Chat.question_text)
        .limit(limit)
        .all()
    )
    return [{"question": r.question_text, "count": r.cnt} for r in rows]
