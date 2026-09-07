import requests

from job_radar.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from job_radar.models import RawJob


def send_telegram_message(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notifier] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set - printing instead of sending:")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    if not resp.ok:
        print(f"[notifier] Telegram send failed: {resp.status_code} {resp.text}")


def format_job_alert(job: RawJob, score: int, matched: list[str]) -> str:
    matched_str = ", ".join(matched) if matched else "-"
    return (
        f"🚨 <b>New job — {job.company}</b>\n"
        f"<b>{job.title}</b>\n"
        f"📍 {job.location or 'n/a'}\n"
        f"Score: {score} | Matched: {matched_str}\n"
        f"Source: {job.source}\n"
        f"{job.url}"
    )
