"""Telegram sending + minimal command polling. Token/chat id come ONLY from environment (GitHub Secrets)."""
import html, os
import httpx

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self, dry=False):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.dry = dry or not (self.token and self.chat_id)
        self.sent = []          # kept for dry-run inspection

    def send(self, text: str) -> bool:
        self.sent.append(text)
        if self.dry:
            print("[TELEGRAM dry-run]\n" + text + "\n")
            return True
        try:
            r = httpx.post(API.format(token=self.token, method="sendMessage"), timeout=20,
                           json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML",
                                 "disable_web_page_preview": True})
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def updates(self, offset=None):
        if self.dry:
            return []
        r = httpx.get(API.format(token=self.token, method="getUpdates"), timeout=20,
                      params={"offset": offset, "timeout": 0})
        return r.json().get("result", []) if r.status_code == 200 else []


esc = html.escape
