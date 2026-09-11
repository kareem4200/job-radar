# job-radar

Personal job-posting radar for robotics roles in Germany.

Polls 33 companies' applicant-tracking systems directly, using their public
feeds, and pushes a Telegram message when a new role matches — instead of
waiting on LinkedIn's daily digest.

LinkedIn is structurally behind: it scrapes ATS feeds on a cycle (every six
hours for ATS partners) and then batches alerts into a once-a-day email. The
job is live on the company's own careers page the moment a recruiter hits
publish. This polls that source directly.

## How it works

```
config/companies.yaml
        │
        ▼
  ATS adapter  ──────────────  8 supported platforms
        │
        ▼
  SQLite: seen this job id before?  ──▶ yes, skip
        │ no
        ▼
  fetch description (lazily — only for new jobs)
        │
        ▼
  score against config/keywords.yaml
        │
        ▼
  score >= MIN_SCORE_TO_ALERT?  ──▶ no, record silently
        │ yes
        ▼
  Telegram
```

Runs on GitHub Actions every 20 min, 06:00–22:59 UTC, Mon–Sat. The seen-jobs
SQLite file is committed back to the repo so state survives between runs.

## Supported ATS platforms

| ats | identifier | notes |
|---|---|---|
| `personio` | subdomain, or a full host if non-standard | `region: de`/`com` |
| `greenhouse` | board token | no EU API host exists — token works globally |
| `ashby` | board name | |
| `lever` | site slug | `region: eu` for EU-hosted |
| `teamtailor` | full careers-site base URL | reads `/jobs.rss` |
| `smartrecruiters` | company id (case-sensitive) | `region: de` filters server-side — **use it**, big boards truncate |
| `successfactors` | careers-site base URL | reads the undocumented `/sitemal.xml` RSS |
| `workday` | `tenant/wd/site` | **undocumented endpoint**, expect occasional breakage |

Not supportable: join.com and softgarden (auth-walled), Avature, and custom
in-house systems. Those companies sit in `companies.yaml` disabled, grouped
by what to do about them instead.

## Setup

```bash
poetry install
poetry run pytest                       # 10 tests
cp .env.example .env                    # add your Telegram bot token + chat id
```

Telegram: message @BotFather, `/newbot`, then message your bot once and read
`chat.id` from `https://api.telegram.org/bot<TOKEN>/getUpdates`.

## Daily use

```bash
# check every enabled company's feed — read-only, no alerts, no db writes
poetry run python -m job_radar.healthcheck
poetry run python -m job_radar.healthcheck --sample        # also score 3 jobs each
poetry run python -m job_radar.healthcheck --ats personio  # narrow it down

# the actual run
poetry run python -m job_radar.main

# identify an unknown company's ATS from its careers URL
poetry run python -m job_radar.discover urls.txt
```

`healthcheck --sample` is the tuning loop: it shows which jobs would alert
and, crucially, **which keyword caused it**, so a bad alert tells you exactly
what to fix.

## Tuning

Everything lives in `config/keywords.yaml`. Scoring is plain weighted
substring matching — no ML — so any score is explainable in seconds.

| where | high_value | medium_value | exclude |
|---|---|---|---|
| title/department | +20 | +8 | **hard reject** |
| description | +8 | +2 | ignored |

Three rules that matter, all learned from real runs:

- **An exclude term in the title is a hard reject**, not a penalty. A
  keyword-rich description was out-scoring a −40 penalty, so "Senior Robotics
  Engineer" alerted anyway.
- **A lone high-value word found only in the description is discounted to 3.**
  Big employers open every posting with "…a global leader in robotics…",
  which was pushing unrelated backend roles over the line.
- **Description-level excludes are disabled.** They fired on boilerplate
  ("report to the Head of…", "work with sales") and penalised good jobs.

`location_exclude` is checked against title *and* location, because several
feeds are global and SuccessFactors bakes the city into the title rather than
publishing a location field.

Threshold: `MIN_SCORE_TO_ALERT` in `job_radar/config.py`, default 20,
overridable with `JOB_RADAR_MIN_SCORE`. Swept against 21 real postings: 20
kept 10/10 good roles with 0/11 bad. Re-sweep if you change keywords much.

```bash
JOB_RADAR_MIN_SCORE=0 poetry run python -m job_radar.main   # prove Telegram works
```

## Deploying

1. Push to GitHub (private repo — your target-company list is your research).
2. **Settings → Secrets and variables → Actions**: add `TELEGRAM_BOT_TOKEN`
   and `TELEGRAM_CHAT_ID`.
3. **Settings → Actions → General → Workflow permissions → Read and write.**
   New repos default to read-only, which makes the database commit fail 403
   while everything else looks green. This is the usual silent failure.
4. **Actions → Job Radar → Run workflow** — don't wait for cron.
5. Confirm the log shows `errors=0` and that `data/seen_jobs.sqlite3` got a
   fresh commit from `job-radar-bot`.

## Inspecting the database

```sql
SELECT company, COUNT(*) n FROM seen_jobs GROUP BY company ORDER BY n DESC;
SELECT first_seen_at, company, title FROM seen_jobs ORDER BY first_seen_at DESC LIMIT 20;
SELECT source, COUNT(*) FROM seen_jobs GROUP BY source;
```

Stores `fingerprint, company, source, title, location, url, first_seen_at` —
not score or description. Use `healthcheck --sample` for scoring questions.

To force a test alert (a fresh baseline never alerts by design):

```sql
DELETE FROM seen_jobs WHERE fingerprint IN
  (SELECT fingerprint FROM seen_jobs WHERE company='NEURA Robotics' LIMIT 5);
```
Deleting only *some* of a company's rows matters — delete all of them and the
company re-baselines silently instead.

## Known limitations

- **Baselining is per company.** The first time a company is seen, its whole
  board is recorded with no alerts. That's what lets you enable 20 companies
  at once without a flood. Silence after adding a company is correct.
- **Airbus returns 500 = the page cap.** Workday has no simple country
  filter, so its French roles bloat the database. They score below threshold,
  so they don't alert.
- **Some Personio tenants publish no descriptions** (cellumation, Unchained,
  fruitcore), so those fall back to title-only scoring.
- **The seen-jobs DB is committed on every change.** Git can't delta binaries,
  so history grows. If the repo gets heavy, lower `MAX_PAGES` in the Workday
  and SmartRecruiters adapters or move the DB to the Actions cache.
- **`discover.py` is weak.** It does a plain HTTP GET and greps for ATS URL
  patterns, so it misses JS-rendered careers pages — which is most of them.
  Clicking Apply on a real posting and reading the domain is more reliable.