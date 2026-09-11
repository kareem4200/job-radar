"""
Pre-flight check: hit every enabled company's ATS feed once and report what
came back. Read-only - touches no database, sends no alerts.

    poetry run python -m job_radar.healthcheck
    poetry run python -m job_radar.healthcheck --ats successfactors
    poetry run python -m job_radar.healthcheck --sample

Use this before deploying, and any time a company goes suspiciously quiet.
Reading a focused OK/FAIL table beats scanning 35 companies' worth of run
logs for the one line that matters.
"""

import argparse
import sys
import time

from job_radar.adapters import ADAPTERS
from job_radar.config import MIN_SCORE_TO_ALERT, load_companies, load_keywords
from job_radar.filters import score_job


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ats", help="only check companies on this ATS")
    ap.add_argument("--company", help="only check this company (substring match)")
    ap.add_argument(
        "--sample",
        action="store_true",
        help="also score 3 jobs per company, to sanity-check keywords.yaml",
    )
    args = ap.parse_args()

    companies = [c for c in load_companies() if c.enabled]
    if args.ats:
        companies = [c for c in companies if c.ats == args.ats]
    if args.company:
        companies = [c for c in companies if args.company.lower() in c.name.lower()]

    keywords = load_keywords() if args.sample else {}

    print(f"Checking {len(companies)} enabled companies")
    print(f"Alert threshold: {MIN_SCORE_TO_ALERT} (JOB_RADAR_MIN_SCORE)\n")
    print(f"{'':<4}{'COMPANY':<30}{'ATS':<16}{'JOBS':>6}  {'TIME':>7}  NOTE")
    print("-" * 96)

    ok = fail = empty = 0
    failures = []

    for c in companies:
        adapter = ADAPTERS.get(c.ats)
        if adapter is None:
            print(f"{'!':<4}{c.name:<30}{c.ats:<16}{'-':>6}  {'-':>7}  no adapter registered")
            fail += 1
            failures.append((c.name, f"unknown ats '{c.ats}'"))
            continue

        t0 = time.time()
        try:
            jobs = adapter.fetch_jobs(c)
        except Exception as exc:
            dt = time.time() - t0
            msg = str(exc).split("\n")[0][:60]
            print(f"{'FAIL':<4}{c.name:<30}{c.ats:<16}{'-':>6}  {dt:>6.1f}s  {msg}")
            fail += 1
            failures.append((c.name, msg))
            continue

        dt = time.time() - t0
        n = len(jobs)
        with_desc = sum(1 for j in jobs if j.description)
        if n == 0:
            # Not an error: an empty board means the identifier resolved and
            # they simply aren't hiring. A WRONG identifier raises instead.
            print(f"{'--':<4}{c.name:<30}{c.ats:<16}{0:>6}  {dt:>6.1f}s  board empty (id is valid)")
            empty += 1
        else:
            note = f"{with_desc}/{n} have descriptions"
            if with_desc == 0:
                note += "  <-- title-only scoring for this company"
            print(f"{'OK':<4}{c.name:<30}{c.ats:<16}{n:>6}  {dt:>6.1f}s  {note}")
            ok += 1

        if args.sample and jobs:
            for j in sorted(
                jobs, key=lambda x: score_job(x, keywords)[0], reverse=True
            )[:3]:
                sc, matched = score_job(j, keywords)
                flag = "ALERT" if sc >= MIN_SCORE_TO_ALERT else "     "
                print(f"        {flag} {sc:>5}  {j.title[:52]:<52} {','.join(matched[:4])}")

    print("-" * 96)
    print(f"OK {ok}   empty {empty}   FAILED {fail}")
    if failures:
        print("\nFailures to fix or disable in config/companies.yaml:")
        for name, msg in failures:
            print(f"  - {name}: {msg}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()