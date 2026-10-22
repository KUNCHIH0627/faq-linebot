from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KeywordIn(BaseModel):
    word: str
    weight: int = Field(3, ge=1)


class FaqCreate(BaseModel):
    category: str
    question: str
    answer: str
    is_active: bool = True
    course_codes: list[str] = Field(min_length=1)  # 例如 ["DB", "WEB"]，課程要先存在
    keywords: list[KeywordIn] = []


class CourseResponse(BaseModel):
    code: str
    name: str


class FaqResponse(BaseModel):
    faq_id: int
    category: str
    question: str
    answer: str
    is_active: bool
    courses: list[CourseResponse]
    keywords: list[KeywordIn]  # word 是正規化後的字串
    since: Optional[datetime] = None
