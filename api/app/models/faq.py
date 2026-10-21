from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from ..core.database import Base


class Faq(Base):
    """一則常見問答。keywords 用逗號分隔，比對時會優先看關鍵字。"""

    __tablename__ = "faq"

    id = Column(Integer, primary_key=True, index=True)
    course = Column(String(50), nullable=False, index=True)  # 例如：網頁程式設計、資料庫系統
    category = Column(String(50), nullable=True)  # 例如：作業、考試、SQL
    question = Column(String(300), nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)  # "join,連接,inner join"
    created_at = Column(DateTime, server_default=func.now())


class QuestionLog(Base):
    """每次有人在 LINE 問問題就記一筆，之後拿來做「常見問題排行榜」。"""

    __tablename__ = "question_log"

    id = Column(Integer, primary_key=True, index=True)
    line_user_id = Column(String(64), nullable=True)
    question_text = Column(Text, nullable=False)
    faq_id = Column(Integer, ForeignKey("faq.id", ondelete="SET NULL"), nullable=True)
    matched = Column(Boolean, nullable=False, default=False)  # 有沒有找到答案
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("idx_question_log_faq_time", "faq_id", "created_at"),)
