"""新增 / 修改 FAQ 時共用的寫入邏輯（seed 和 CRUD API 都用這裡）。"""
from sqlalchemy.orm import Session

from ..models.faq import Category, Course, Faq, FaqKeyword, Keyword
from .matcher import normalize


class UnknownCourseError(ValueError):
    def __init__(self, codes: list[str]):
        super().__init__(f"找不到課程代碼：{', '.join(codes)}")
        self.codes = codes


def get_or_create_category(db: Session, name: str) -> Category:
    cat = db.query(Category).filter(Category.name == name).one_or_none()
    if not cat:
        cat = Category(name=name)
        db.add(cat)
        db.flush()
    return cat


def get_or_create_keyword(db: Session, word: str) -> Keyword:
    kw = db.query(Keyword).filter(Keyword.word == word).one_or_none()
    if not kw:
        kw = Keyword(word=word)
        db.add(kw)
        db.flush()
    return kw


def save_faq(
    db: Session,
    faq: Faq,
    *,
    category: str,
    question: str,
    answer: str,
    is_active: bool = True,
    course_codes: list[str],
    keywords: list[tuple[str, int]],
) -> Faq:
    """把欄位、課程、關鍵字一次寫進 faq（新的或既有的都可以），不 commit。
    關鍵字會先正規化；正規化後重複的只留 weight 較大的那個。"""
    codes = list(dict.fromkeys(course_codes))
    courses = db.query(Course).filter(Course.code.in_(codes)).all()
    missing = sorted(set(codes) - {c.code for c in courses})
    if missing:
        raise UnknownCourseError(missing)

    weights: dict[str, int] = {}
    for word, weight in keywords:
        w = normalize(word)
        if w:
            weights[w] = max(weight, weights.get(w, 0))

    faq.category = get_or_create_category(db, category)
    faq.question = question
    faq.answer = answer
    faq.is_active = is_active
    faq.courses = sorted(courses, key=lambda c: codes.index(c.code))
    if faq.faq_id is None:
        db.add(faq)
    faq.keyword_links = []
    db.flush()  # 先清掉舊的 faq_keyword，避免和新的主鍵撞在一起
    faq.keyword_links = [
        FaqKeyword(keyword=get_or_create_keyword(db, w), weight=wt) for w, wt in weights.items()
    ]
    db.flush()
    return faq
