#!/usr/bin/env python3
"""
Score GitHub repositories against data/featured_repos_rubric.json and update
data/linkedin.json featured_repos (max 3).

Re-runs when older than reevaluate_days (default 7). Use --force to score now.

Usage:
  python scripts/score_featured_repos.py           # score only (report)
  python scripts/score_featured_repos.py --apply # update linkedin.json if due
  python scripts/score_featured_repos.py --force --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = REPO_ROOT / "data" / "featured_repos_rubric.json"
LINKEDIN_PATH = REPO_ROOT / "data" / "linkedin.json"
SCORES_PATH = REPO_ROOT / "data" / "featured_repos_scores.json"
LAST_RUN_PATH = REPO_ROOT / "data" / ".featured_repos_last_run"


def github_get(url: str) -> list | dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "EshwarCVS-featured-rubric",
    }
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code} for {url}: {e.read().decode()[:200]}")
        return []


def fetch_candidate_repos(rubric: dict) -> list[dict]:
    repos: dict[str, dict] = {}
    sources = rubric.get("sources", {})

    for user in sources.get("users", []):
        page = 1
        while page <= 3:
            data = github_get(
                f"https://api.github.com/users/{user}/repos"
                f"?sort=pushed&per_page=100&page={page}"
            )
            if not isinstance(data, list) or not data:
                break
            for r in data:
                if r.get("private"):
                    continue
                full = r.get("full_name", "")
                if full:
                    repos[full] = r
            page += 1

    for org in sources.get("orgs", []):
        page = 1
        while page <= 3:
            data = github_get(
                f"https://api.github.com/orgs/{org}/repos"
                f"?sort=pushed&per_page=100&page={page}"
            )
            if not isinstance(data, list) or not data:
                break
            for r in data:
                if r.get("private"):
                    continue
                full = r.get("full_name", "")
                if full:
                    repos[full] = r
            page += 1

    return list(repos.values())


def days_since(iso: str) -> int:
    if not iso:
        return 9999
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return 9999


def score_repo(repo: dict, rubric: dict) -> dict:
    full_name = repo.get("full_name", "")
    name = repo.get("name", "")
    owner = (repo.get("owner") or {}).get("login", "")
    description = (repo.get("description") or "").strip()
    stars = repo.get("stargazers_count", 0) or 0
    is_fork = bool(repo.get("fork"))
    pushed_days = days_since(repo.get("pushed_at", ""))
    boosts = rubric.get("manual_boosts", {})
    exclude = set(rubric.get("exclude", []))

    breakdown: dict[str, float] = {}
    notes: list[str] = []

    if full_name in exclude:
        return {
            "full_name": full_name,
            "total": -999,
            "breakdown": {},
            "notes": ["excluded by rubric"],
        }

    if repo.get("private"):
        return {
            "full_name": full_name,
            "total": -999,
            "breakdown": {},
            "notes": ["private repo — excluded"],
        }

    # Ownership (20)
    ownership = 20.0 if not is_fork else 5.0
    if is_fork:
        notes.append("fork — lower ownership score")
    breakdown["ownership"] = ownership

    # Impact (20) — stars log scale, cap at 20
    impact = min(20.0, stars * 2) if stars else (8.0 if description else 2.0)
    if stars >= 5:
        notes.append(f"{stars} stars")
    breakdown["impact"] = impact

    # Relevance (20) — has description + language signals real project
    relevance = 10.0
    if description and len(description) > 20:
        relevance += 8.0
    lang = repo.get("language")
    if lang:
        relevance += 2.0
    breakdown["relevance"] = min(20.0, relevance)

    # Recency (20)
    if pushed_days <= 14:
        recency = 20.0
    elif pushed_days <= 30:
        recency = 16.0
    elif pushed_days <= 90:
        recency = 10.0
    elif pushed_days <= 180:
        recency = 5.0
    else:
        recency = 1.0
    breakdown["recency"] = recency
    notes.append(f"last push {pushed_days}d ago")

    # Unboosted repos with no traction shouldn't beat established projects on recency alone
    if full_name not in boosts and stars == 0:
        breakdown["recency"] = round(recency * 0.5, 1)
        notes.append("recency damped (no boost/stars)")

    # Story (20) — description quality
    story = 5.0
    if description:
        story += min(15.0, len(description) / 4)
    breakdown["story"] = min(20.0, story)

    manual = float(boosts.get(full_name, 0))
    if manual:
        notes.append(f"manual boost +{manual}")
    breakdown["manual_boost"] = manual

    if is_fork:
        breakdown["fork_penalty"] = -15.0
    if not description:
        breakdown["no_description_penalty"] = -10.0

    total = sum(breakdown.values())

    return {
        "full_name": full_name,
        "name": name,
        "org": owner,
        "url": repo.get("html_url", ""),
        "description": description,
        "language": lang or "",
        "stars": stars,
        "pushed_at": repo.get("pushed_at", ""),
        "total": round(total, 1),
        "breakdown": breakdown,
        "notes": notes,
    }


def build_highlight(scored: dict, rubric: dict) -> str:
    pinned = {
        p["full_name"]: p.get("highlight", "")
        for p in rubric.get("pinned", [])
    }
    if scored["full_name"] in pinned and pinned[scored["full_name"]]:
        return pinned[scored["full_name"]]

    desc = truncate(scored.get("description", ""), 80)
    org = scored.get("org", "")
    templates = rubric.get("highlight_templates", {})
    if org and org != "EshwarCVS":
        tpl = templates.get("org", "{description}")
    elif org == "EshwarCVS":
        tpl = templates.get("personal", "{description}")
    else:
        tpl = templates.get("default", "{description}")
    return tpl.format(description=desc or "Active repository")


def truncate(text: str, max_len: int) -> str:
    return text[:max_len] + ("..." if len(text) > max_len else "")


def select_featured(scored: list[dict], rubric: dict) -> list[dict]:
    max_n = rubric.get("max_featured", 3)
    pinned_names = [p["full_name"] for p in rubric.get("pinned", [])]
    by_name = {s["full_name"]: s for s in scored if s["total"] > -100}

    selected: list[dict] = []
    used: set[str] = set()

    for pin in rubric.get("pinned", []):
        full = pin["full_name"]
        if full in by_name and full not in used:
            entry = dict(by_name[full])
            entry["priority"] = pin.get("priority", len(selected) + 1)
            entry["highlight"] = pin.get("highlight") or build_highlight(entry, rubric)
            selected.append(entry)
            used.add(full)
        if len(selected) >= max_n:
            return selected[:max_n]

    ranked = sorted(
        [s for s in scored if s["full_name"] not in used and s["total"] > -100],
        key=lambda x: x["total"],
        reverse=True,
    )
    for entry in ranked:
        if len(selected) >= max_n:
            break
        entry = dict(entry)
        entry["priority"] = len(selected) + 1
        entry["highlight"] = build_highlight(entry, rubric)
        selected.append(entry)
        used.add(entry["full_name"])

    return selected[:max_n]


def to_linkedin_featured(selected: list[dict]) -> list[dict]:
    return [
        {
            "priority": item["priority"],
            "name": item["name"],
            "org": item["org"],
            "url": item["url"],
            "description": item["description"],
            "language": item.get("language", ""),
            "highlight": item.get("highlight", ""),
            "score": item.get("total"),
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
        for item in selected
    ]


def is_due(rubric: dict) -> bool:
    days = rubric.get("reevaluate_days", 7)
    if not LAST_RUN_PATH.exists():
        return True
    try:
        last = datetime.fromisoformat(LAST_RUN_PATH.read_text().strip())
        return datetime.now(timezone.utc) - last >= timedelta(days=days)
    except ValueError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Score repos for featured section")
    parser.add_argument("--apply", action="store_true", help="Write results to linkedin.json")
    parser.add_argument("--force", action="store_true", help="Ignore reevaluate_days interval")
    args = parser.parse_args()

    rubric = json.loads(RUBRIC_PATH.read_text())
    if not args.force and not is_due(rubric):
        print(f"Featured repo rubric: skipped (re-evaluate every {rubric.get('reevaluate_days', 7)} days)")
        print("Use --force to run now.")
        return 0

    print("Featured repository rubric — scoring candidates...")
    raw_repos = fetch_candidate_repos(rubric)
    if not raw_repos:
        print("No repositories fetched. Check GITHUB_TOKEN or network.")
        return 1

    scored = [score_repo(r, rubric) for r in raw_repos]
    scored.sort(key=lambda x: x["total"], reverse=True)
    selected = select_featured(scored, rubric)

    report = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": rubric.get("version", 1),
        "criteria": rubric.get("criteria", []),
        "selected": [
            {"full_name": s["full_name"], "score": s["total"], "priority": s["priority"]}
            for s in selected
        ],
        "rankings": scored[:15],
    }
    SCORES_PATH.write_text(json.dumps(report, indent=2))

    print(f"\nTop candidates (of {len(scored)} repos):")
    for i, s in enumerate(scored[:8], 1):
        mark = " ★" if any(x["full_name"] == s["full_name"] for x in selected) else ""
        print(f"  {i:2}. {s['total']:5.1f}  {s['full_name']}{mark}")
        print(f"      {', '.join(s['notes'])}")

    print("\nSelected featured (max 3):")
    for s in selected:
        print(f"  #{s['priority']} {s['full_name']} ({s['total']}) — {s.get('highlight', '')}")

    if args.apply:
        linkedin = json.loads(LINKEDIN_PATH.read_text())
        linkedin["featured_repos"] = to_linkedin_featured(selected)
        LINKEDIN_PATH.write_text(json.dumps(linkedin, indent=2) + "\n")
        LAST_RUN_PATH.write_text(datetime.now(timezone.utc).isoformat())
        print(f"\nApplied to {LINKEDIN_PATH.relative_to(REPO_ROOT)}")
        print(f"Audit log: {SCORES_PATH.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
