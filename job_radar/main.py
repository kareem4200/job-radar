import datetime
import sys

from job_radar import storage
from job_radar.adapters import ADAPTERS
from job_radar.config import MIN_SCORE_TO_ALERT, load_companies, load_keywords
from job_radar.filters import score_job
from job_radar.notifier import format_job_alert, send_telegram_message


def run() -> int:
    companies = load_companies()
    keywords = load_keywords()
    now = datetime.datetime.utcnow().isoformat()

    # If the store has no history at all, this is a first/baseline run: every
    # currently-open job would otherwise look "new" and you'd get flooded
    # with alerts for postings that have been up for months. So we record
    # everything as seen but suppress alerts for this run only.
    is_baseline_run = not storage.has_any_seen()
    if is_baseline_run:
        print(
            "[job-radar] No history found - this is a baseline run. "
            "All currently open jobs will be recorded but NOT alerted on. "
            "Future runs will only alert on jobs that are new since this baseline."
        )

    new_count = 0
    alert_count = 0
    errors: list[str] = []

    for company in companies:
        if not company.enabled:
            continue

        adapter = ADAPTERS.get(company.ats)
        if adapter is None:
            errors.append(f"{company.name}: unknown ats '{company.ats}'")
            continue

        try:
            jobs = adapter.fetch_jobs(company)
        except Exception as exc:  # one company's failure should never kill the whole run
            errors.append(f"{company.name} ({company.ats}): {exc}")
            continue

        for job in jobs:
            if not storage.is_new(job.fingerprint):
                continue

            storage.mark_seen(job, now)
            new_count += 1

            if is_baseline_run:
                continue

            score, matched = score_job(job, keywords)
            if score >= MIN_SCORE_TO_ALERT:
                send_telegram_message(format_job_alert(job, score, matched))
                alert_count += 1

    print(
        f"[job-radar] companies={len(companies)} new_jobs={new_count} "
        f"alerts_sent={alert_count} errors={len(errors)}"
    )
    for e in errors:
        print(f"[job-radar][error] {e}")

    # Always exit 0: a bad board token or a transient network error for one
    # company should be visible in the logs, not fail the whole scheduled run.
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
