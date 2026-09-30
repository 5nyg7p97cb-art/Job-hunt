#!/usr/bin/env python3
"""
Entry-level job tracker.
Polls company career boards (Greenhouse, Lever, Ashby, Workday, Gem, Oleeo), filters for
entry-level roles in your locations, and pushes new matches to your phone via ntfy.
No dependencies beyond the Python standard library.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "config.json").read_text())
SEEN_FILE = ROOT / "seen.json"
BOARD_FILE = ROOT / "JOBS.md"
FILTERS = CONFIG["filters"]


# ---------- HTTP ----------
def http_json(url, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"User-Agent": "Mozilla/5.0 (entry-level-job-tracker)", "Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def http_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (entry-level-job-tracker)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


# ---------- Fetchers: each yields {id, title, location, url} ----------
def fetch_greenhouse(slug):
    data = http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    for j in data.get("jobs", []):
        yield {
            "id": f"gh-{slug}-{j['id']}",
            "title": j["title"],
            "location": (j.get("location") or {}).get("name", ""),
            "url": j["absolute_url"],
        }


def fetch_lever(slug):
    for j in http_json(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location", "")]
        yield {
            "id": f"lv-{slug}-{j['id']}",
            "title": j["text"],
            "location": " / ".join(filter(None, locs)),
            "url": j["hostedUrl"],
        }


def fetch_ashby(slug):
    data = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        if j.get("isRemote"):
            locs.append("Remote")
        yield {
            "id": f"ab-{slug}-{j['id']}",
            "title": j["title"],
            "location": " / ".join(filter(None, locs)),
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
        }


def fetch_workday(board_url, search_text=""):
    # board_url looks like https://acme.wd5.myworkdayjobs.com/External (a locale like /en-US/ is fine)
    m = re.match(r"https://([^/]+)/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", board_url)
    host, site = m.group(1), m.group(2)
    tenant = host.split(".")[0]
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    offset, total = 0, None
    while True:
        data = http_json(api, {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": search_text})
        posts = data.get("jobPostings", [])
        if total is None:
            total = data.get("total", 0)  # Workday only reports total on the first page
        for j in posts:
            path = j.get("externalPath", "")
            yield {
                "id": f"wd-{tenant}-{path}",
                "title": j.get("title", ""),
                "location": j.get("locationsText", ""),
                "url": f"https://{host}/{site}{path}",
            }
        offset += 20
        if not posts or offset >= total or offset >= 2000:
            break


def fetch_gem(slug):
    # Gem ATS public Job Board API (boards live at jobs.gem.com/<slug>)
    data = http_json(f"https://api.gem.com/job_board/v0/{slug}/job_posts/")
    posts = data if isinstance(data, list) else (data.get("job_posts") or data.get("jobs") or [])
    for j in posts:
        locs = []
        loc = j.get("location")
        locs.append(loc.get("name", "") if isinstance(loc, dict) else (loc or ""))
        for o in j.get("offices") or []:
            ol = o.get("location")
            locs += [o.get("name", ""), ol.get("name", "") if isinstance(ol, dict) else (ol or "")]
        locs = list(dict.fromkeys(filter(None, locs)))
        yield {
            "id": f"gem-{slug}-{j.get('id')}",
            "title": j.get("title", ""),
            "location": " / ".join(locs),
            "url": j.get("absolute_url") or j.get("url") or f"https://jobs.gem.com/{slug}/{j.get('id')}",
        }


def fetch_oleeo(board_url):
    # Oleeo boards (*.tal.net) publish an RSS feed next to the job board page.
    feed_url = board_url.split("/adv")[0].rstrip("/") + "/feed"
    text = http_text(feed_url)
    if "<rss" not in text[:500] and "<feed" not in text[:500]:
        raise RuntimeError("board is behind a bot check / no RSS feed (check it manually)")
    import xml.etree.ElementTree as ET
    for item in ET.fromstring(text).iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = strip_html(item.findtext("description"))
        paren = re.search(r"\(([^)]*)\)\s*$", title)  # e.g. "Analyst - Tech (New York)"
        yield {
            "id": f"ol-{link or title}",
            "title": title,
            "location": paren.group(1) if paren else "",
            # use the "(City)" in the title when present; otherwise let the description decide
            "match_text": "" if paren else f"{title} {desc[:400]}",
            "url": link or board_url,
        }


def fetch(company):
    ats, slug = company["ats"], company["slug"]
    if ats == "greenhouse":
        return fetch_greenhouse(slug)
    if ats == "lever":
        return fetch_lever(slug)
    if ats == "ashby":
        return fetch_ashby(slug)
    if ats == "workday":
        return fetch_workday(slug, company.get("search_text", ""))
    if ats == "gem":
        return fetch_gem(slug)
    if ats == "oleeo":
        return fetch_oleeo(slug)
    raise ValueError(f"unknown ats '{ats}'")


# ---------- Filtering ----------
def has_any(text, words):
    return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, re.I) for w in words)


def matches(job, company):
    """Company settings: include_title / exclude_title / locations REPLACE the defaults;
    extra_include / extra_exclude ADD to the defaults."""
    title = job["title"]
    exclude = company.get("exclude_title", FILTERS["exclude_title"]) + company.get("extra_exclude", [])
    if has_any(title, exclude):
        return False
    include = company.get("include_title", FILTERS["include_title"]) + company.get("extra_include", [])
    if include and not has_any(title, include):
        return False
    locations = company.get("locations", FILTERS["locations"])
    where = f"{job['location']} {job.get('match_text', '')}"
    if locations and not has_any(where, locations):
        return False
    return True


# ---------- Notifications (ntfy.sh push to phone) ----------
def notify(title, message, click=None):
    print(f"NOTIFY: {title} | {message} | {click or ''}")
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    payload = {"topic": topic, "title": title, "message": message, "tags": ["briefcase"]}
    if click:
        payload["click"] = click
    try:
        http_json("https://ntfy.sh/", payload)
    except Exception as e:
        print(f"ntfy failed: {e}", file=sys.stderr)


# ---------- Board (JOBS.md) ----------
def write_board(current, new_ids, errors):
    cell = lambda s: str(s).replace("|", "/").strip()
    lines = [
        "# Entry-level openings",
        "",
        f"{len(current)} matching roles open. 🆕 = found in the latest run.",
        "",
        "| | Company | Role | Location |",
        "|---|---|---|---|",
    ]
    for j in sorted(current, key=lambda j: (j["id"] not in new_ids, j["company"].lower(), j["title"])):
        flag = "🆕" if j["id"] in new_ids else ""
        lines.append(f"| {flag} | {cell(j['company'])} | [{cell(j['title'])}]({j['url']}) | {cell(j['location'])} |")
    if errors:
        lines += ["", "## Boards that failed this run", ""] + [f"- {cell(e)}" for e in errors]
    BOARD_FILE.write_text("\n".join(lines) + "\n")


# ---------- Main ----------
def main():
    first_run = not SEEN_FILE.exists()
    state = {} if first_run else json.loads(SEEN_FILE.read_text())
    if isinstance(state, list):  # older format
        state = {"seen": state}
    seen = set(state.get("seen", []))
    was_failing = set(state.get("failing", []))
    current, new, errors, failing = [], [], [], set()
    companies = [c for c in CONFIG["companies"] if c.get("enabled", True)]

    for c in companies:
        try:
            jobs = list(fetch(c))
        except Exception as e:
            errors.append(f"{c['name']}: {e}")
            failing.add(c["name"])
            print(f"{c['name']}: ERROR {e}", file=sys.stderr)
            if c["name"] not in was_failing:
                notify(f"Tracker can't read {c['name']}", str(e)[:200])
            continue
        hits = [dict(j, company=c["name"]) for j in jobs if matches(j, c)]
        print(f"{c['name']}: {len(jobs)} open, {len(hits)} match")
        current += hits
        new += [j for j in hits if j["id"] not in seen]

    if first_run:
        notify("Job tracker is live", f"Watching {len(companies)} companies. {len(current)} matching roles open right now.")
    elif len(new) > 8:
        by_co = {}
        for j in new:
            by_co[j["company"]] = by_co.get(j["company"], 0) + 1
        summary = ", ".join(f"{co} ({n})" for co, n in by_co.items())
        notify(f"{len(new)} new entry-level roles", summary)
    else:
        for j in new:
            notify(f"New at {j['company']}", f"{j['title']}\n{j['location']}", j["url"])

    state = {"seen": sorted(seen | {j["id"] for j in current}), "failing": sorted(failing)}
    SEEN_FILE.write_text(json.dumps(state, indent=0))
    write_board(current, {j["id"] for j in new} if not first_run else set(), errors)


if __name__ == "__main__":
    main()
