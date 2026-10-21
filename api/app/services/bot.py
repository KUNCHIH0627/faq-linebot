"""機器人的「大腦」：收到一句話，決定要回什麼，並寫入紀錄。"""
from sqlalchemy.orm import Session

from ..models.faq import Faq, QuestionLog
from .matcher import find_match

HELP_WORDS = {"選單", "說明", "help", "?", "？", "menu"}


def help_text(db: Session) -> str:
    courses = [c for (c,) in db.query(Faq.course).distinct().order_by(Faq.course).all()]
    lines = ["你好！我是課程 FAQ 小幫手，直接問我問題就可以，例如："]
    lines += [f"・{c} 的相關問題" for c in courses] or ["（目前還沒有 FAQ 資料）"]
    lines.append("\n也可以直接輸入關鍵字，像是「JOIN」、「作業」。")
    return "\n".join(lines)


def format_answer(faq: Faq, suggestions: list[Faq]) -> str:
    text = f"【{faq.course}】{faq.question}\n\n{faq.answer}"
    if suggestions:
        text += "\n\n你可能還想問：\n" + "\n".join(f"・{s.question}" for s in suggestions)
    return text


def handle_text(db: Session, user_id: str | None, text: str) -> str:
    text = (text or "").strip()
    if text.lower() in HELP_WORDS:
        return help_text(db)

    result = find_match(text, db.query(Faq).all())

    db.add(
        QuestionLog(
            line_user_id=user_id,
            question_text=text,
            faq_id=result.best.id if result.best else None,
            matched=result.best is not None,
        )
    )
    db.commit()

    if result.best:
        return format_answer(result.best, result.suggestions)

    reply = "抱歉，我找不到相關的答案，這題我會記下來。"
    if result.suggestions:
        reply += "\n\n你是不是想問：\n" + "\n".join(f"・{s.question}" for s in result.suggestions)
    else:
        reply += "\n輸入「選單」可以看我能回答哪些課程。"
    return reply
