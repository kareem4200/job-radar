import datetime
import sys

from job_radar import storage
from job_radar.adapters import ADAPTERS
from job_radar.config import MIN_SCORE_TO_ALERT, load_companies, load_keywords
from job_radar.filters import score_job
from job_radar.notifier import format_error_alert, format_job_alert, send_telegram_message


def run() -> int:
    companies = load_companies()
    keywords = load_keywords()
    now = datetime.datetime.utcnow().isoformat()

    new_count = 0
    alert_count = 0
    baseline_companies: list[str] = []
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

        # Baseline per COMPANY, not globally: the first time we see THIS
        # company, every job it currently has open would otherwise look
        # "new" - record them but don't alert. This is what lets you add
        # a batch of 20 companies at once without a flood of alerts for
        # postings that have been open for months. Companies you've seen
        # before are unaffected.
        is_baseline_for_company = not storage.has_any_seen_for_company(company.name)
        if is_baseline_for_company:
            baseline_companies.append(company.name)

        for job in jobs:
            if not storage.is_new(job.fingerprint):
                continue

            storage.mark_seen(job, now)
            new_count += 1

            if is_baseline_for_company:
                continue

            # Some ATSs (SmartRecruiters, Workday) don't return descriptions
            # in their list endpoint. Fetch it now - but only for jobs that
            # are genuinely new AND not part of a baseline sweep, so a
            # 2,000-posting employer costs us zero extra requests per run
            # when nothing has changed.
            if job.description is None:
                try:
                    job.description = adapter.fetch_description(company, job)
                except Exception as exc:
                    errors.append(f"{company.name} description {job.external_id}: {exc}")

            score, matched = score_job(job, keywords)
            if score >= MIN_SCORE_TO_ALERT:
                send_telegram_message(format_job_alert(job, score, matched))
                alert_count += 1

    if baseline_companies:
        print(f"[job-radar] baseline (no alerts) for: {', '.join(baseline_companies)}")

    print(
        f"[job-radar] companies={len(companies)} new_jobs={new_count} "
        f"alerts_sent={alert_count} errors={len(errors)}"
    )
    for e in errors:
        print(f"[job-radar][error] {e}")

    if errors:
        send_telegram_message(format_error_alert(errors))

    # Always exit 0: a bad board token or a transient network error for one
    # company should be visible in the logs, not fail the whole scheduled run.
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()