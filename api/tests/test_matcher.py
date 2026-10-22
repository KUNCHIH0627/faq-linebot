"""直接測比對邏輯（不經過資料庫）。"""
from app.services.matcher import (
    MATCH_THRESHOLD,
    FaqKeywords,
    KeywordWeight,
    find_match,
    normalize,
)

_ids = iter(range(1, 10_000))


def faq(faq_id, *kws):
    """faq(1, ("join", 3), ("連接", 2))"""
    return FaqKeywords(faq_id, tuple(KeywordWeight(next(_ids), normalize(w), wt) for w, wt in kws))


def test_normalize():
    assert normalize("  Inner JOIN？ ") == "innerjoin"
    assert normalize("「主鍵」，外鍵！") == "主鍵外鍵"
    assert normalize(None) == ""


def test_keyword_contained_in_question_after_normalize():
    r = find_match("請問 Inner-Join 是什麼？", [faq(1, ("inner join", 3))])
    assert r.status == "answered" and r.best.faq_id == 1


def test_score_is_sum_of_hit_weights():
    r = find_match("作業怎麼繳交", [faq(1, ("作業", 2), ("繳交", 2), ("期限", 1))])
    assert r.best.score == 4
    assert [k.word for k in r.best.hits] == ["作業", "繳交"]


def test_threshold_exactly_three_answers():
    assert MATCH_THRESHOLD == 3
    r = find_match("join", [faq(1, ("join", 3))])
    assert r.status == "answered"


def test_below_threshold_only_suggests():
    r = find_match("作業", [faq(1, ("作業", 2)), faq(2, ("考試", 3))])
    assert r.status == "suggest"
    assert r.best is None
    assert [c.faq_id for c in r.suggestions] == [1]


def test_suggestions_capped_at_three_and_sorted():
    faqs = [faq(i, ("作業", 1), *([("繳交", 1)] if i == 4 else [])) for i in range(1, 6)]
    r = find_match("作業繳交", faqs)
    assert r.status == "suggest"
    assert [c.faq_id for c in r.suggestions] == [4, 1, 2]


def test_no_hit_is_none():
    r = find_match("學校餐廳幾點開", [faq(1, ("join", 3))])
    assert r.status == "none" and r.candidates == [] and r.hit_keyword_ids == []


def test_empty_question_is_none():
    assert find_match("？？  ", [faq(1, ("join", 3))]).status == "none"


def test_tie_break_by_hit_count():
    # 兩則都是 4 分：faq 2 命中 2 個關鍵字，faq 1 只命中 1 個
    r = find_match("ab cd", [faq(1, ("ab", 4)), faq(2, ("ab", 2), ("cd", 2))])
    assert [c.faq_id for c in r.candidates] == [2, 1]


def test_tie_break_by_total_keyword_length():
    # 同分、同命中數：faq 2 的關鍵字比較長
    r = find_match("fastapi 是什麼", [faq(1, ("api", 3)), faq(2, ("fastapi", 3))])
    assert [c.faq_id for c in r.candidates] == [2, 1]


def test_tie_break_by_smaller_faq_id():
    r = find_match("作業", [faq(7, ("作業", 3)), faq(3, ("作業", 3))])
    assert [c.faq_id for c in r.candidates] == [3, 7]


def test_answered_suggestions_exclude_best():
    faqs = [faq(1, ("join", 3)), faq(2, ("join", 1)), faq(3, ("join", 1)), faq(4, ("join", 1)), faq(5, ("join", 1))]
    r = find_match("join", faqs)
    assert r.best.faq_id == 1
    assert [c.faq_id for c in r.suggestions] == [2, 3, 4]


def test_hit_keyword_ids_cover_all_faqs():
    f1, f2 = faq(1, ("join", 3)), faq(2, ("left join", 3), ("合併", 1))
    r = find_match("left join", [f1, f2])
    expected = {f1.keywords[0].keyword_id, f2.keywords[0].keyword_id}
    assert set(r.hit_keyword_ids) == expected
