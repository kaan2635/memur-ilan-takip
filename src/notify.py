"""Bildirim: ntfy.sh (opsiyonel), Telegram (opsiyonel). GitHub Issue workflow'da açılır."""
import os
import requests


def ntfy(baslik: str, govde: str, link: str = None, oncelik: str = "default"):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    h = {"Title": baslik.encode("utf-8"), "Priority": oncelik, "Tags": "briefcase"}
    if link:
        h["Click"] = link
    r = requests.post(f"{server}/{topic}", data=govde.encode("utf-8"), headers=h, timeout=20)
    return r.ok


def telegram(metin: str):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      json={"chat_id": chat, "text": metin[:4000], "disable_web_page_preview": True}, timeout=20)
    return r.ok
