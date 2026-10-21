"""把使用者的問題拿去比對 FAQ。

做法刻意簡單、好解釋（Demo 被問到可以直接講）：
  1. 關鍵字命中：問題裡出現 FAQ 設定的關鍵字，每個 +3 分
  2. 問句包含：問題和 FAQ 問題文字互相包含，+5 分
  3. 字面相似度：用 difflib 算兩句的相似比例（0~1），乘 3
分數最高且 >= MATCH_THRESHOLD 就當作答案；
分數介於 SUGGEST_THRESHOLD ~ MATCH_THRESHOLD 的，列成「你是不是想問」。
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

MATCH_THRESHOLD = 3.0
SUGGEST_THRESHOLD = 1.5

_PUNCT = re.compile(r"[\s　，,。.？?！!、；;：:\-_/\\()（）\[\]「」『』\"'`]+")


def normalize(text: str) -> str:
    return _PUNCT.sub("", (text or "").lower())


def split_keywords(keywords: str | None) -> list[str]:
    if not keywords:
        return []
    parts = re.split(r"[,，;；\n]", keywords)
    return [normalize(p) for p in parts if normalize(p)]


def score(question: str, faq) -> float:
    q = normalize(question)
    if not q:
        return 0.0
    fq = normalize(faq.question)

    s = 0.0
    for kw in split_keywords(faq.keywords):
        if kw in q:
            s += 3
    if len(q) >= 2 and fq and (fq in q or q in fq):
        s += 5
    s += SequenceMatcher(None, q, fq).ratio() * 3
    return s


@dataclass
class MatchResult:
    best: object | None  # 命中的 Faq，沒有就是 None
    suggestions: list  # 「你是不是想問」的 Faq 清單


def find_match(question: str, faqs: Iterable, max_suggestions: int = 3) -> MatchResult:
    scored = sorted(((score(question, f), f) for f in faqs), key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] >= MATCH_THRESHOLD:
        best = scored[0][1]
        rest = [f for s, f in scored[1:] if s >= SUGGEST_THRESHOLD]
        return MatchResult(best=best, suggestions=rest[:max_suggestions])
    suggestions = [f for s, f in scored if s >= SUGGEST_THRESHOLD]
    return MatchResult(best=None, suggestions=suggestions[:max_suggestions])
