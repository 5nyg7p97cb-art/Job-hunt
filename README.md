# Job Hunt

A tracker for early-career jobs in finance, consulting, strategy, analytics, technology, and AI.

The expanded configuration monitors 39 career boards across 37 companies, focusing on New York and remote opportunities.

## How it works

1. Checks company career boards.
2. Filters openings by title and location.
3. Identifies new matching jobs.
4. Sends notifications through ntfy.
5. Updates JOBS.md with openings and check results.

Checks are scheduled every 30 minutes. GitHub may delay scheduled runs.

## View openings

Open [JOBS.md](JOBS.md) to see matching jobs, the last check time, and results for each career board.

## Supported platforms

- Greenhouse
- Lever
- Ashby
- Workday
- Gem
- Oleeo

## Repository files

| File | Purpose |
|---|---|
| config.json | Companies and filters |
| tracker.py | Job fetching and notifications |
| seen.json | Previously seen jobs |
| JOBS.md | Openings and check results |
| .github/workflows/main.yml | Scheduled workflow |

## Setup

1. Add config.json and tracker.py to the repository root.
2. Add the workflow at .github/workflows/main.yml.
3. Subscribe to a private, hard-to-guess topic in the ntfy app.
4. Open GitHub Settings → Secrets and variables → Actions.
5. Add a secret named NTFY_TOPIC containing your topic name.
6. Open Actions → Job tracker → Run workflow.

Without NTFY_TOPIC, the tracker updates JOBS.md but does not send phone notifications.

## Filters

The tracker targets analyst, associate, junior, graduate, entry-level, and rotational roles.

Senior positions, management roles, internships, and certain higher-level titles are excluded.

Edit config.json to change companies, titles, or locations. Company-specific settings can override the default filters.

## Tracker health

JOBS.md shows:

- Last check time in UTC
- Current matching openings
- Total and matching jobs for each board
- Boards that failed

The report also appears in the GitHub Actions run summary.

No new notifications can mean there are no unseen matching jobs. If every enabled board fails, the workflow reports a failure.

## Limitations

- Scheduled checks may be delayed.
- Career boards may change or block requests.
- An empty feed does not necessarily mean there are no openings.
- Remote jobs are not automatically restricted to the United States.
- Some Workday listings require checking the job page for location.
- Title filters do not guarantee entry-level experience requirements.

## Requirements

Python 3.12. No additional Python packages are required.
