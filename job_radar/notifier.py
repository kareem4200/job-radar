import html

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
        # Printed, not raised: one bad message must not abort the whole run.
        # Watch for this line in the Actions log - a 400 here means the
        # message body was malformed, a 401/404 means bad token/chat id.
        print(f"[notifier] Telegram send FAILED: {resp.status_code} {resp.text}")


def format_error_alert(errors: list[str]) -> str:
    """Build the Telegram message for a run that hit adapter/description errors.

    Truncated defensively: Telegram rejects a message over 4096 chars
    outright, and a single flaky ATS can otherwise repeat the same error
    across many companies in one run.
    """
    lines = "\n".join(html.escape(e) for e in errors)
    text = f"⚠️ <b>job-radar: {len(errors)} error(s) this run</b>\n{lines}"
    if len(text) > 4000:
        text = text[:4000] + "\n… (truncated)"
    return text


def format_job_alert(job: RawJob, score: int, matched: list[str]) -> str:
    """Build the Telegram message.

    Everything interpolated MUST be HTML-escaped: we send with
    parse_mode=HTML, and Telegram rejects the whole message with
    400 "can't parse entities" if a bare &, < or > appears outside a tag.
    German robotics titles are full of ampersands - "Robotik &
    Automatisierung", "Vision & Perception", "Data & Cloud" - so without
    escaping, a large share of alerts would silently fail to send.
    """
    matched_str = ", ".join(matched) if matched else "-"
    return (
        f"🚨 <b>New job — {html.escape(job.company)}</b>\n"
        f"<b>{html.escape(job.title)}</b>\n"
        f"📍 {html.escape(job.location or 'n/a')}\n"
        f"Score: {score} | Matched: {html.escape(matched_str)}\n"
        f"Source: {html.escape(job.source)}\n"
        f"{job.url}"
    )