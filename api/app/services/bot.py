"""機器人的「大腦」：收到一句話，決定要回什麼，並寫入紀錄。"""
from collections import defaultdict

from sqlalchemy.orm import Session

from ..models.faq import Chat, ChatFaq, ChatKeyword, Course, Faq, FaqKeyword, Keyword
from .matcher import FaqKeywords, KeywordWeight, find_match

HELP_WORDS = {"選單", "說明", "help", "?", "？", "menu"}


def help_text(db: Session) -> str:
    courses = [c for (c,) in db.query(Course.name).order_by(Course.course_id).all()]
    lines = ["你好！我是課程 FAQ 小幫手，直接問我問題就可以，例如："]
    lines += [f"・{c} 的相關問題" for c in courses] or ["（目前還沒有 FAQ 資料）"]
    lines.append("\n也可以直接輸入關鍵字，像是「JOIN」、「作業」。")
    return "\n".join(lines)


def load_faq_keywords(db: Session) -> list[FaqKeywords]:
    """把所有啟用中的 FAQ 和它們的關鍵字、weight 讀出來，交給 matcher。"""
    rows = (
        db.query(FaqKeyword.faq_id, Keyword.keyword_id, Keyword.word, FaqKeyword.weight)
        .join(Keyword, Keyword.keyword_id == FaqKeyword.keyword_id)
        .join(Faq, Faq.faq_id == FaqKeyword.faq_id)
        .filter(Faq.is_active.is_(True))
        .all()
    )
    grouped: dict[int, list[KeywordWeight]] = defaultdict(list)
    for faq_id, keyword_id, word, weight in rows:
        grouped[faq_id].append(KeywordWeight(keyword_id, word, weight))
    return [FaqKeywords(faq_id, tuple(kws)) for faq_id, kws in grouped.items()]


def course_label(faq: Faq) -> str:
    return "／".join(c.name for c in faq.courses)


def format_answer(faq: Faq, suggestions: list[Faq]) -> str:
    text = f"【{course_label(faq)}】{faq.question}\n\n{faq.answer}"
    if suggestions:
        text += "\n\n你可能還想問：\n" + "\n".join(f"・{s.question}" for s in suggestions)
    return text


def handle_text(db: Session, user_id: str | None, text: str) -> str:
    text = (text or "").strip()
    if text.lower() in HELP_WORDS:
        return help_text(db)

    result = find_match(text, load_faq_keywords(db))

    chat = Chat(line_user_id=user_id, question_text=text)
    db.add(chat)
    db.flush()  # 先拿到 chat_id
    db.add_all(ChatKeyword(chat_id=chat.chat_id, keyword_id=kid) for kid in result.hit_keyword_ids)

    # 只有答出來才寫 chat_faq：rank 1 是答案，rank 2 以後是「你可能還想問」
    # 沒答出來（只有建議或查無資料）就沒有 chat_faq，統計時自然算成未回答
    if result.best:
        replied = [result.best, *result.suggestions]
        db.add_all(
            ChatFaq(chat_id=chat.chat_id, faq_id=c.faq_id, score=c.score, rank=i)
            for i, c in enumerate(replied, start=1)
        )
    db.commit()

    if result.best:
        best = db.get(Faq, result.best.faq_id)
        return format_answer(best, [db.get(Faq, c.faq_id) for c in result.suggestions])

    reply = "抱歉，我找不到相關的答案，這題我會記下來。"
    if result.suggestions:
        reply += "\n\n你是不是想問：\n" + "\n".join(
            f"・{db.get(Faq, c.faq_id).question}" for c in result.suggestions
        )
    else:
        reply += "\n輸入「選單」可以看我能回答哪些課程。"
    return reply
