import json

from .conftest import sign


def post_message(client, text, user="U123", secret="test-secret"):
    body = json.dumps(
        {"events": [{"type": "message", "replyToken": "rt", "source": {"userId": user},
                     "message": {"type": "text", "text": text}}]}
    ).encode()
    return client.post("/api/webhook", content=body,
                       headers={"X-Line-Signature": sign(body, secret)})


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


def test_answer_by_keyword(client, sent):
    assert post_message(client, "請問 JOIN 是什麼").status_code == 200
    assert len(sent) == 1
    assert "INNER JOIN" in sent[0][1]


def test_answer_by_question_text(client, sent):
    post_message(client, "PRIMARY KEY 和 FOREIGN KEY 差在哪")
    assert "唯一識別" in sent[0][1]


def test_unanswered_is_logged_and_suggested(client, sent):
    post_message(client, "學校餐廳幾點開")
    assert "找不到" in sent[0][1]
    r = client.get("/api/analytics/unanswered")
    assert r.json() == [{"question": "學校餐廳幾點開", "count": 1}]


def test_help_menu(client, sent):
    post_message(client, "選單")
    assert "資料庫系統" in sent[0][1] and "網頁程式設計" in sent[0][1]


def test_top_faqs_ranking(client, sent):
    for _ in range(3):
        post_message(client, "JOIN 是什麼")
    post_message(client, "什麼是 API")
    top = client.get("/api/analytics/top-faqs").json()
    assert top[0]["question"] == "什麼是 JOIN？" and top[0]["count"] == 3
    assert top[1]["question"] == "什麼是 API？" and top[1]["count"] == 1


def test_non_text_event_ignored(client, sent):
    body = json.dumps({"events": [{"type": "follow", "replyToken": "rt"}]}).encode()
    r = client.post("/api/webhook", content=body, headers={"X-Line-Signature": sign(body)})
    assert r.status_code == 200 and sent == []


def test_faq_crud(client):
    r = client.post("/api/faqs", json={"course": "測試", "question": "Q?", "answer": "A"})
    assert r.status_code == 201
    fid = r.json()["id"]
    assert client.put(f"/api/faqs/{fid}", json={"course": "測試", "question": "Q2?", "answer": "A"}).json()["question"] == "Q2?"
    assert client.delete(f"/api/faqs/{fid}").status_code == 204
    assert client.get(f"/api/faqs/{fid}").status_code == 404
