# Entry-level job tracker

Checks company career boards every 30 minutes, keeps entry-level roles in your
locations, and pushes new ones to your phone. `JOBS.md` is always the live list.

## Setup (≈10 min)
1. Install the **ntfy** app (iOS/Android), subscribe to a hard-to-guess topic, e.g. `nicole-jobs-8f3k2`.
2. Create a GitHub repo and upload these files (keep the `.github/workflows` folder).
3. Repo → Settings → Secrets and variables → Actions → New secret: `NTFY_TOPIC` = your topic.
4. Actions tab → "Job tracker" → **Run workflow**. You'll get a "tracker is live" push.

Run locally anytime: `NTFY_TOPIC=your-topic python tracker.py`

## Adding a company
Open its careers page and look at where "Apply" links go:

| Link contains | ats | slug |
|---|---|---|
| `boards.greenhouse.io/XYZ` or `job-boards.greenhouse.io/XYZ` | greenhouse | XYZ |
| `jobs.lever.co/XYZ` | lever | XYZ |
| `jobs.ashbyhq.com/XYZ` | ashby | XYZ |
| `XYZ.wd5.myworkdayjobs.com/Site` | workday | the full board URL |
| `jobs.gem.com/XYZ` | gem | XYZ |
| `XYZ.tal.net/...` | oleeo | the full job-board URL |

Per-company settings: `include_title` / `exclude_title` / `locations` replace the defaults;
`extra_include` / `extra_exclude` add to them. `"enabled": false` pauses a company.
If a board stops working you get one push saying so.
Companies on other career sites aren't supported.

## Tuning
- Too much noise → trim `include_title` (e.g. drop "associate").
- Missing roles → check the `JOBS.md` "failed" section, or loosen `locations`.
- Private repo: switch cron to hourly to stay within free Actions minutes.
