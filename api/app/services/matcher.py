"""把使用者的問題拿去比對 FAQ —— 只用關鍵字。

做法刻意簡單、好解釋（Demo 被問到可以直接講）：
  1. 正規化：轉小寫、去掉標點與空白（關鍵字和問題都一樣處理）
  2. 某個關鍵字「被包含在問題中」就算命中
  3. 每則 FAQ 的分數 = 命中關鍵字的 weight 總和
  4. 最高分 >= MATCH_THRESHOLD 才回答；同分時依序比：命中關鍵字數多、命中關鍵字總長度長、faq_id 小
  5. 分數 > 0 但未達門檻：列最多 3 則「你是不是想問」
  6. 完全沒命中：查無資料
這個檔案不碰資料庫，方便單獨測試。
"""
import re
from dataclasses import dataclass, field
from typing import Iterable

MATCH_THRESHOLD = 3
MAX_SUGGESTIONS = 3

_PUNCT = re.compile(r"[\s　，,。.？?！!、；;：:\-_/\\()（）\[\]「」『』\"'`]+")


def normalize(text: str | None) -> str:
    return _PUNCT.sub("", (text or "").lower())


@dataclass(frozen=True)
class KeywordWeight:
    keyword_id: int
    word: str  # 已正規化
    weight: int


@dataclass(frozen=True)
class FaqKeywords:
    faq_id: int
    keywords: tuple[KeywordWeight, ...]


@dataclass
class Candidate:
    faq_id: int
    score: int
    hits: list[KeywordWeight]

    @property
    def sort_key(self):
        return (-self.score, -len(self.hits), -sum(len(k.word) for k in self.hits), self.faq_id)


@dataclass
class MatchResult:
    status: str  # "answered" / "suggest" / "none"
    candidates: list[Candidate] = field(default_factory=list)  # 分數 > 0 的 FAQ，已排序
    hit_keyword_ids: list[int] = field(default_factory=list)  # 這次提問命中的所有關鍵字

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.status == "answered" else None

    @property
    def suggestions(self) -> list[Candidate]:
        """answered 時是「你可能還想問」，suggest 時是「你是不是想問」。"""
        rest = self.candidates[1:] if self.status == "answered" else self.candidates
        return rest[:MAX_SUGGESTIONS]


def find_match(question: str, faqs: Iterable[FaqKeywords]) -> MatchResult:
    q = normalize(question)
    candidates: list[Candidate] = []
    hit_ids: set[int] = set()
    if q:
        for f in faqs:
            hits = [k for k in f.keywords if k.word and k.word in q]
            if hits:
                candidates.append(Candidate(f.faq_id, sum(k.weight for k in hits), hits))
                hit_ids.update(k.keyword_id for k in hits)
    candidates.sort(key=lambda c: c.sort_key)

    if not candidates:
        status = "none"
    elif candidates[0].score >= MATCH_THRESHOLD:
        status = "answered"
    else:
        status = "suggest"
    return MatchResult(status=status, candidates=candidates, hit_keyword_ids=sorted(hit_ids))
