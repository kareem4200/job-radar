# job-radar

Personal job-posting radar for robotics/engineering roles in Germany.

Polls company ATS platforms (Greenhouse, Personio, Lever) directly using
their public, unauthenticated job APIs, keeps track of what it's already
seen, and pushes a Telegram message the moment a new job matches your
keywords — instead of waiting for LinkedIn's daily/weekly alert digest.

**Suggested GitHub repo name:** `job-radar` (or `robotics-job-radar` if you
want it more self-descriptive). Keep it private if you don't want your
target-company list public.

This is **Phase 1**: a working end-to-end pipeline for ~1-3 ATS types and a
handful of companies, running on a free GitHub Actions cron schedule, with no
database server, no dashboard, and no hosting to manage. Prove it's useful
before expanding it (see "Roadmap" at the bottom).

---

## How it works

```
config/companies.yaml  →  ATS adapter (Greenhouse / Personio / Lever)
                              ↓
                        fetch current jobs
                              ↓
                    SQLite: is this job new?  →  no → skip
                              ↓ yes
                        keyword scoring (config/keywords.yaml)
                              ↓
                    score ≥ threshold?  →  no → record, don't alert
                              ↓ yes
                        Telegram message
```

Runs on a GitHub Actions schedule (default: every 20 minutes, 06:00-22:59
UTC, Mon-Sat). The "seen jobs" SQLite database is committed back to the repo
after each run so state persists between runs without needing an external
database.

**First run behavior:** the first time it runs against a company, every
currently-open job would otherwise look "new." To avoid a flood of alerts
for postings that have been up for months, the very first run for an empty
database records everything as seen but sends **no alerts**. Only jobs that
appear *after* that baseline trigger a Telegram message.

---

## Project layout

```
job-radar/
├── README.md
├── pyproject.toml              # poetry dependencies
├── .env.example                # copy to .env for local runs
├── .gitignore
├── config/
│   ├── companies.yaml          # target companies + which ATS they use
│   └── keywords.yaml           # relevance keyword lists + weights
├── job_radar/
│   ├── __init__.py
│   ├── config.py                # loads yaml config + env vars
│   ├── models.py                 # RawJob dataclass + dedup fingerprint
│   ├── storage.py                # SQLite seen-jobs store
│   ├── filters.py                # keyword scoring
│   ├── notifier.py               # Telegram message sending/formatting
│   ├── main.py                   # orchestrator - the actual "job-radar" run
│   ├── discover.py               # Phase-0 helper: detect ATS from career URLs
│   └── adapters/
│       ├── base.py                # adapter interface
│       ├── greenhouse.py
│       ├── personio.py
│       └── lever.py
├── tests/
│   ├── test_filters.py
│   └── test_models.py
├── data/
│   └── seen_jobs.sqlite3        # created + committed automatically by the Action
└── .github/workflows/
    └── job-radar.yml            # scheduled run
```

---

## Setup

### 1. Install dependencies locally (optional, for testing before deploying)

```bash
poetry install
poetry run pytest        # should show 6 passed
```

### 2. Create a Telegram bot (a few minutes)

1. Open Telegram, message **@BotFather**, send `/newbot`, follow the
   prompts. You'll get a bot token like `123456789:AAExample...`.
2. Message your new bot anything (e.g. "hi") so it can see your chat.
3. Get your chat ID: visit
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser after
   step 2, and read `message.chat.id` from the JSON response.
4. Put both values in `.env` (copy from `.env.example`) for local testing.

### 3. Phase 0 — find real ATS identifiers for your target companies

Don't guess board tokens. Put your target companies' career-page URLs in a
text file and run the discovery helper:

```bash
poetry run python -m job_radar.discover urls.txt
```

It fetches each page and looks for known Greenhouse/Lever/Personio/
SmartRecruiters/Workday URL patterns, and prints ready-to-paste YAML
snippets. **Always verify the result** (open the resulting API/feed URL in a
browser) before enabling a company — see the caveats in
`job_radar/discover.py` about JS-rendered career pages not being detectable
this way.

Paste verified entries into `config/companies.yaml` and set `enabled: true`.

### 4. Tune keywords

Edit `config/keywords.yaml`. Scoring is deliberately simple and transparent:
`high_value` = +20, `medium_value` = +8, `exclude` = -40, matched against
`"<title> <department>"`. The alert threshold (`MIN_SCORE_TO_ALERT`,
default 15) lives in `job_radar/config.py` — override it via the
`JOB_RADAR_MIN_SCORE` env var if you don't want to touch code.

### 5. Run it once locally to seed the baseline

```bash
poetry run python -m job_radar.main
```

You'll see a "baseline run" message and a summary line. No alerts will fire
on this first run by design.

### 6. Deploy to GitHub Actions

```bash
git init
git add .
git commit -m "Phase 1: job radar"
git remote add origin git@github.com:<you>/job-radar.git
git push -u origin main
```

Then in the repo: **Settings → Secrets and variables → Actions**, add
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repository secrets.

The workflow (`.github/workflows/job-radar.yml`) will then run on its cron
schedule automatically. You can also trigger it manually from the **Actions**
tab (`workflow_dispatch`) to test it end-to-end before waiting for the cron.

---

## Design notes / things I'd want you to know before relying on this

- **Only one seed company (`Wandelbots`, Personio) is a verified real
  entry.** The others in `companies.yaml` (NEURA, KUKA, Franka, Agile
  Robots, ANYbotics) are clearly-marked **placeholders** with
  `identifier: CHANGE_ME` and `enabled: false` — I did not fabricate board
  tokens for companies I couldn't verify. Run `discover.py` to fill these in
  for real.
- **The SQLite file is committed to git by the Action.** That's a
  deliberate, low-effort persistence choice for a personal-scale tool (a
  few hundred rows). It's not something you'd do for a multi-user system —
  if this grows past Phase 1, move to GitHub Actions cache or an external
  DB instead.
- **Poll frequency and politeness:** Greenhouse doesn't publish a hard rate
  limit but recommends against aggressive polling; every 15-30 minutes is
  plenty for a personal tool and won't stress anyone's infrastructure.
  Companies without a public ATS API (proprietary career pages) are **not**
  handled by this Phase 1 — don't write custom HTML scrapers per company;
  if you need that later, point a change-detection tool (e.g.
  changedetection.io) at those specific pages instead of maintaining
  bespoke parsers.
- **Errors in one company never kill the whole run** — check the Action
  logs for `[job-radar][error]` lines if a company stops returning jobs
  (wrong token, ATS migration, etc.).
- Only Greenhouse, Personio, and Lever are implemented. Workday and
  SmartRecruiters are flagged by `discover.py` but have no adapter yet —
  they're real APIs but noticeably more involved to integrate; that's a
  Phase 2 candidate, not a Phase 1 one.

## Roadmap (do NOT build this yet — see chat for the reasoning)

- **Phase 2:** StepStone / Bundesagentur für Arbeit searches (both support
  filtering by posting recency), expand to 50-75 companies, add
  SmartRecruiters adapter.
- **Phase 3, optional:** dashboard, application tracker, more companies —
  only if Phase 1 is actually getting used and producing useful alerts.
