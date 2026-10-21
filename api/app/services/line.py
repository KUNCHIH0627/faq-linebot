"""跟 LINE 溝通的兩件事：驗證簽章、回覆訊息。"""
import base64
import hashlib
import hmac
import logging
import os

import httpx

logger = logging.getLogger("line")

REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def get_secret() -> str:
    return os.getenv("LINE_CHANNEL_SECRET", "")


def get_token() -> str:
    return os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")


def verify_signature(body: bytes, signature: str | None) -> bool:
    """LINE 會用 Channel Secret 對「原始 body」做 HMAC-SHA256 再 base64，放在 X-Line-Signature。
    我們自己算一次，一樣才代表請求真的來自 LINE。"""
    secret = get_secret()
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


async def reply_text(reply_token: str, text: str) -> None:
    """用 replyToken 回覆一則文字（LINE 單則文字上限 5000 字）。失敗只記錄，不讓 webhook 掛掉。"""
    token = get_token()
    if not token:
        logger.error("沒有設定 LINE_CHANNEL_ACCESS_TOKEN，無法回覆")
        return
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text[:5000]}]}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                REPLY_URL, json=payload, headers={"Authorization": f"Bearer {token}"}
            )
        if resp.status_code != 200:
            logger.error("LINE 回覆失敗 %s: %s", resp.status_code, resp.text)
    except httpx.HTTPError as e:
        logger.error("LINE 回覆發生網路錯誤: %s", e)
