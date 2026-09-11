"""
Phase 0 helper: given a list of company career-page URLs, try to detect which
ATS each one uses so you can fill in config/companies.yaml with real values
instead of guessing board tokens.

Usage:
    poetry run python -m job_radar.discover urls.txt

urls.txt: one career-page URL per line, e.g.
    https://www.neura-robotics.com/careers
    https://www.kuka.com/en-de/careers
    # lines starting with # are ignored

Limitations (read this before trusting the output):
  - This does a plain HTTP GET and greps the HTML/redirect URL for known ATS
    URL patterns. It does NOT execute JavaScript, so career pages built as a
    single-page app that loads jobs via a background API call after page load
    may show no match even though they DO use one of these ATS platforms.
    If you get no match, open the page in a browser, open dev tools -> Network
    tab, reload, and look for a request to boards-api.greenhouse.io,
    api.lever.co, or *.jobs.personio.de.
  - Always verify a detected identifier by pasting the resulting API/feed URL
    into a browser before enabling that company in companies.yaml.
"""

import re
import sys

import requests

PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([a-zA-Z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_-]+)")),
    ("personio", re.compile(r"([a-zA-Z0-9_-]+)\.jobs\.personio\.(?:de|com)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)")),
    # Not implemented as adapters yet (Phase 2 candidates) - still worth flagging:
    ("smartrecruiters", re.compile(r"careers\.smartrecruiters\.com/([a-zA-Z0-9_-]+)")),
    ("workday", re.compile(r"([a-zA-Z0-9_-]+)\.wd\d?\.myworkdayjobs\.com")),
]


def detect(url: str):
    try:
        resp = requests.get(
            url, timeout=15, headers={"User-Agent": "job-radar-discover/0.1"}, allow_redirects=True
        )
    except requests.RequestException as exc:
        print(f"  ! could not fetch {url}: {exc}")
        return None

    haystack = resp.url + "\n" + resp.text
    for ats, pattern in PATTERNS:
        m = pattern.search(haystack)
        if m:
            return ats, m.group(1)
    return None


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: poetry run python -m job_radar.discover urls.txt")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print("# Review and verify EVERY entry before pasting into config/companies.yaml\n")
    for url in urls:
        result = detect(url)
        if result:
            ats, identifier = result
            print(f'- name: "CHANGE_ME"   # detected from {url}')
            print(f"  ats: {ats}")
            print(f"  identifier: {identifier}")
            print("  enabled: true")
            print()
        else:
            print(f"# no known ATS pattern found on {url} - check manually (may be Workday/SAP/proprietary)\n")


if __name__ == "__main__":
    main()