"""資料表定義（ER 模型）。

實體表：course、category、faq、keyword、chat
關聯表：faq_course（FAQ ↔ 課程，多對多）、faq_keyword（FAQ ↔ 關鍵字，帶 weight）、
        chat_faq（提問 ↔ 回覆的 FAQ，rank = 1 是最終答案）、chat_keyword（提問命中的關鍵字）
「這次有沒有答出來」不存在 chat 上，而是看 chat_faq 有沒有紀錄。
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class Course(Base):
    __tablename__ = "course"

    course_id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)  # 例如：DB、WEB
    name = Column(String(50), nullable=False)  # 例如：資料庫系統


class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # 例如：作業、考試、SQL


class Faq(Base):
    """一則常見問答。屬於哪些課程看 faq_course，關鍵字看 faq_keyword。"""

    __tablename__ = "faq"

    faq_id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("category.category_id"), nullable=False, index=True)
    question = Column(String(300), nullable=False)
    answer = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    since = Column(DateTime, server_default=func.now())

    category = relationship("Category")
    courses = relationship("Course", secondary="faq_course", order_by="Course.course_id")
    keyword_links = relationship(
        "FaqKeyword", cascade="all, delete-orphan", order_by="FaqKeyword.keyword_id"
    )


class Keyword(Base):
    """word 存正規化後的字串（小寫、無標點空白），UNIQUE 才不會因寫法不同而重複。"""

    __tablename__ = "keyword"

    keyword_id = Column(Integer, primary_key=True)
    word = Column(String(100), unique=True, nullable=False)


class Chat(Base):
    """每次有人在 LINE 問問題就記一筆。"""

    __tablename__ = "chat"

    chat_id = Column(Integer, primary_key=True)
    line_user_id = Column(String(64), nullable=True)
    question_text = Column(Text, nullable=False)
    since = Column(DateTime, server_default=func.now())


class FaqCourse(Base):
    __tablename__ = "faq_course"

    faq_id = Column(Integer, ForeignKey("faq.faq_id", ondelete="CASCADE"), primary_key=True)
    course_id = Column(Integer, ForeignKey("course.course_id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (Index("idx_faq_course_course", "course_id"),)


class FaqKeyword(Base):
    __tablename__ = "faq_keyword"

    faq_id = Column(Integer, ForeignKey("faq.faq_id", ondelete="CASCADE"), primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keyword.keyword_id", ondelete="CASCADE"), primary_key=True)
    weight = Column(Integer, nullable=False, default=3, server_default="3")

    keyword = relationship("Keyword")

    __table_args__ = (
        CheckConstraint("weight > 0", name="ck_faq_keyword_weight"),
        Index("idx_faq_keyword_keyword", "keyword_id"),
    )


class ChatFaq(Base):
    """這次提問回覆了哪些 FAQ：rank = 1 是答案，rank 2 以後是「你可能還想問」。"""

    __tablename__ = "chat_faq"

    chat_id = Column(Integer, ForeignKey("chat.chat_id", ondelete="CASCADE"), primary_key=True)
    faq_id = Column(Integer, ForeignKey("faq.faq_id", ondelete="CASCADE"), primary_key=True)
    score = Column(Integer, nullable=False)  # 命中關鍵字的 weight 總和
    rank = Column(Integer, nullable=False)
    is_helpful = Column(Boolean, nullable=True)  # 使用者回饋，還沒回饋就是 NULL

    __table_args__ = (Index("idx_chat_faq_faq_rank", "faq_id", "rank"),)


class ChatKeyword(Base):
    __tablename__ = "chat_keyword"

    chat_id = Column(Integer, ForeignKey("chat.chat_id", ondelete="CASCADE"), primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keyword.keyword_id", ondelete="CASCADE"), primary_key=True)
