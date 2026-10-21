from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FaqCreate(BaseModel):
    course: str
    category: Optional[str] = None
    question: str
    answer: str
    keywords: Optional[str] = None


class FaqResponse(FaqCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: Optional[datetime] = None
