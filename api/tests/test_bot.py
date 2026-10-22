import json

from app.models.faq import Chat, ChatFaq, ChatKeyword, Faq, Keyword

from .conftest import sign


def post_message(client, text, user="U123", secret="test-secret"):
    body = json.dumps(
        {"events": [{"type": "message", "replyToken": "rt", "source": {"userId": user},
                     "message": {"type": "text", "text": text}}]}
    ).encode()
    return client.post("/api/webhook", content=body,
                       headers={"X-Line-Signature": sign(body, secret)})


def faq_id_of(db, question):
    return db.query(Faq.faq_id).filter(Faq.question == question).scalar()


def new_faq(**kw):
    data = {"category": "測試", "question": "Q?", "answer": "A", "course_codes": ["DB"]}
    data.update(kw)
    return data


# ---------------- 簽章與事件 ----------------

def test_verify_button_empty_events(client):
    body = b'{"destination":"U0","events":[]}'
    r = client.post("/api/webhook", content=body, headers={"X-Line-Signature": sign(body)})
    assert r.status_code == 200


def test_bad_signature_rejected(client, sent):
    r = post_message(client, "join", secret="wrong")
    assert r.status_code == 400
    assert sent == []


def test_missing_signature_rejected(client):
    r = client.post("/api/webhook", content=b'{"events":[]}')
    assert r.status_code == 400


def test_non_text_event_ignored(client, sent, db):
    body = json.dumps({"events": [{"type": "follow", "replyToken": "rt"}]}).encode()
    r = client.post("/api/webhook", content=body, headers={"X-Line-Signature": sign(body)})
    assert r.status_code == 200 and sent == []
    assert db.query(Chat).count() == 0


def test_help_menu(client, sent, db):
    post_message(client, "選單")
    assert "資料庫系統" in sent[0][1] and "網頁程式設計" in sent[0][1]
    assert db.query(Chat).count() == 0  # 指令不算提問


# ---------------- 比對與回覆 ----------------

def test_answer_by_keyword(client, sent):
    assert post_message(client, "請問 JOIN 是什麼").status_code == 200
    assert len(sent) == 1
    assert "INNER JOIN" in sent[0][1]
    assert sent[0][1].startswith("【資料庫系統】")


def test_answer_by_multiple_keywords(client, sent):
    post_message(client, "PRIMARY KEY 和 FOREIGN KEY 差在哪")
    assert "唯一識別" in sent[0][1]


def test_answer_writes_chat_keyword_and_chat_faq(client, sent, db):
    post_message(client, "作業怎麼繳交", user="Uabc")
    chat = db.query(Chat).one()
    assert chat.line_user_id == "Uabc" and chat.question_text == "作業怎麼繳交"

    words = {w for (w,) in db.query(Keyword.word).join(ChatKeyword).filter(ChatKeyword.chat_id == chat.chat_id)}
    assert words == {"作業", "繳交"}

    rows = db.query(ChatFaq).filter(ChatFaq.chat_id == chat.chat_id).order_by(ChatFaq.rank).all()
    assert rows[0].rank == 1 and rows[0].faq_id == faq_id_of(db, "作業要怎麼繳交？")
    assert rows[0].score == 4 and rows[0].is_helpful is None


def test_answer_also_records_related_candidates(client, sent, db):
    # 「fastapi」裡也包含「api」：文件那則是答案（rank 1），「什麼是 API？」是 rank 2
    post_message(client, "FastAPI 的 API 文件在哪裡看")
    assert "/api/docs" in sent[0][1]
    assert "你可能還想問：\n・什麼是 API？" in sent[0][1]
    ranks = {r.faq_id: r.rank for r in db.query(ChatFaq).all()}
    assert ranks == {faq_id_of(db, "FastAPI 的 API 文件在哪裡看？"): 1, faq_id_of(db, "什麼是 API？"): 2}


def test_below_threshold_suggests_without_chat_faq(client, sent, db):
    post_message(client, "作業")  # 只命中 weight 2 的「作業」，未達門檻 3
    assert "找不到" in sent[0][1]
    assert "你是不是想問：\n・作業要怎麼繳交？" in sent[0][1]
    assert db.query(ChatFaq).count() == 0
    assert [w for (w,) in db.query(Keyword.word).join(ChatKeyword)] == ["作業"]


def test_no_hit_replies_not_found(client, sent, db):
    post_message(client, "學校餐廳幾點開")
    assert "找不到" in sent[0][1] and "選單" in sent[0][1]
    assert "你是不是想問" not in sent[0][1]
    assert db.query(Chat).count() == 1
    assert db.query(ChatKeyword).count() == 0 and db.query(ChatFaq).count() == 0


def test_inactive_faq_not_matched(client, sent, db):
    fid = faq_id_of(db, "什麼是 JOIN？")
    db.get(Faq, fid).is_active = False
    db.commit()
    post_message(client, "join")
    assert "找不到" in sent[0][1]


# ---------------- 多對多：同一則 FAQ 屬於兩門課 ----------------

def test_shared_faq_belongs_to_both_courses(client):
    for code in ("DB", "WEB"):
        questions = [f["question"] for f in client.get("/api/faqs", params={"course": code}).json()]
        assert "作業要怎麼繳交？" in questions
    db_only = [f["question"] for f in client.get("/api/faqs", params={"course": "DB"}).json()]
    assert "什麼是 API？" not in db_only


def test_shared_faq_reply_shows_both_courses(client, sent):
    post_message(client, "交作業")
    assert sent[0][1].startswith("【資料庫系統／網頁程式設計】作業要怎麼繳交？")


def test_courses_endpoint(client):
    assert client.get("/api/courses").json() == [
        {"code": "DB", "name": "資料庫系統"},
        {"code": "WEB", "name": "網頁程式設計"},
    ]


# ---------------- 統計 ----------------

def test_top_faqs_counts_rank_one_only(client, sent):
    for _ in range(3):
        post_message(client, "JOIN 是什麼")
    post_message(client, "什麼是 API")
    post_message(client, "FastAPI 的 API 文件在哪裡看")  # 「什麼是 API？」在這裡是 rank 2，不算
    top = client.get("/api/analytics/top-faqs").json()
    assert [(t["question"], t["count"]) for t in top] == [
        ("什麼是 JOIN？", 3),
        ("什麼是 API？", 1),
        ("FastAPI 的 API 文件在哪裡看？", 1),
    ]
    assert top[0]["rank"] == 1 and top[0]["courses"] == ["資料庫系統"]


def test_top_faqs_lists_all_courses_of_shared_faq(client, sent):
    post_message(client, "作業怎麼繳交")
    top = client.get("/api/analytics/top-faqs").json()
    assert top == [{"rank": 1, "faq_id": top[0]["faq_id"], "question": "作業要怎麼繳交？",
                    "courses": ["資料庫系統", "網頁程式設計"], "count": 1}]


def test_unanswered_counts_chats_without_chat_faq(client, sent):
    post_message(client, "學校餐廳幾點開")
    post_message(client, "學校餐廳幾點開")
    post_message(client, "作業")  # 只有建議，也算未回答
    post_message(client, "join")  # 有答案，不算
    assert client.get("/api/analytics/unanswered").json() == [
        {"question": "學校餐廳幾點開", "count": 2},
        {"question": "作業", "count": 1},
    ]


# ---------------- FAQ CRUD ----------------

def test_faq_crud(client):
    r = client.post("/api/faqs", json=new_faq(
        course_codes=["DB", "WEB"], keywords=[{"word": "Unit Test", "weight": 4}, {"word": "測試"}],
    ))
    assert r.status_code == 201
    body = r.json()
    fid = body["faq_id"]
    assert body["category"] == "測試" and body["is_active"] is True
    assert [c["code"] for c in body["courses"]] == ["DB", "WEB"]
    assert body["keywords"] == [{"word": "unittest", "weight": 4}, {"word": "測試", "weight": 3}]

    r = client.put(f"/api/faqs/{fid}", json=new_faq(question="Q2?", keywords=[{"word": "測試", "weight": 1}]))
    body = r.json()
    assert body["question"] == "Q2?"
    assert [c["code"] for c in body["courses"]] == ["DB"]
    assert body["keywords"] == [{"word": "測試", "weight": 1}]

    assert client.delete(f"/api/faqs/{fid}").status_code == 204
    assert client.get(f"/api/faqs/{fid}").status_code == 404


def test_created_faq_is_matchable(client, sent):
    client.post("/api/faqs", json=new_faq(question="教室在哪？", answer="在管理學院 101", keywords=[{"word": "教室"}]))
    post_message(client, "請問教室在哪")
    assert "管理學院 101" in sent[0][1]


def test_faq_unknown_course_rejected(client):
    r = client.post("/api/faqs", json=new_faq(course_codes=["NOPE"]))
    assert r.status_code == 422 and "NOPE" in r.json()["detail"]


def test_faq_requires_a_course(client):
    assert client.post("/api/faqs", json=new_faq(course_codes=[])).status_code == 422


def test_faq_weight_must_be_positive(client):
    assert client.post("/api/faqs", json=new_faq(keywords=[{"word": "x", "weight": 0}])).status_code == 422


def test_delete_faq_cascades_chat_faq(client, sent, db):
    post_message(client, "join")
    fid = faq_id_of(db, "什麼是 JOIN？")
    assert client.delete(f"/api/faqs/{fid}").status_code == 204
    assert db.query(ChatFaq).count() == 0
    assert db.query(Chat).count() == 1  # 提問紀錄本身保留
