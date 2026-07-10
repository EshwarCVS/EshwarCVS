"""
Fetch activity from GitHub, Substack, and LinkedIn (config-based).
Outputs structured JSON for downstream generators.

GITHUB_TOKEN is read from the process environment (auto-injected in GitHub Actions).
See .env.example for declared env key names.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substack_filters import filter_professional_posts


GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "EshwarCVS")
SUBSTACK_RSS = os.getenv("SUBSTACK_RSS", "https://devdine.substack.com/feed")
LINKEDIN_DATA_PATH = os.getenv("LINKEDIN_DATA_PATH", "data/linkedin.json")


def github_token() -> str:
    """GitHub token from the process environment (Actions injects GITHUB_TOKEN)."""
    return os.getenv("GITHUB_TOKEN", "")


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "EshwarCVS-profile-updater",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_graphql(query: str, variables: dict = None) -> dict:
    """Execute a GitHub GraphQL query."""
    token = github_token()
    if not token:
        print("GitHub GraphQL skipped: no GITHUB_TOKEN available")
        return {}

    headers = {
        **github_headers(),
        "Content-Type": "application/json",
    }
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=payload, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub GraphQL error: {e.code} {e.read().decode()}")
        return {}


def github_rest(endpoint: str) -> dict | list:
    """Execute a GitHub REST API call."""
    req = urllib.request.Request(
        f"https://api.github.com{endpoint}", headers=github_headers()
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"GitHub REST error: {e.code} {e.read().decode()}")
        return {}


def fetch_github_activity() -> dict:
    """Fetch recent GitHub contributions, PRs, commits, reviews."""
    today = datetime.now(timezone.utc)
    since = (today - timedelta(days=7)).isoformat()
    year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0).isoformat()

    # Contribution calendar + recent activity via GraphQL
    query = """
    query($username: String!, $since: DateTime!, $yearStart: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $yearStart) {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                color
              }
            }
          }
        }
        pullRequests(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            title
            url
            state
            repository { nameWithOwner }
            createdAt
            updatedAt
          }
        }
        repositoriesContributedTo(first: 10, orderBy: {field: PUSHED_AT, direction: DESC}, contributionTypes: [COMMIT, PULL_REQUEST, PULL_REQUEST_REVIEW]) {
          nodes {
            nameWithOwner
            url
            description
            pushedAt
            primaryLanguage { name color }
          }
        }
        repositories(first: 10, orderBy: {field: PUSHED_AT, direction: DESC}, ownerAffiliations: OWNER) {
          nodes {
            name
            url
            description
            pushedAt
            primaryLanguage { name color }
            stargazerCount
          }
        }
      }
    }
    """
    variables = {
        "username": GITHUB_USERNAME,
        "since": since,
        "yearStart": year_start,
    }
    result = github_graphql(query, variables)
    user = result.get("data", {}).get("user", {})

    # Recent events via REST (commits, comments, reviews)
    events = github_rest(f"/users/{GITHUB_USERNAME}/events/public?per_page=30")
    recent_events = []
    if isinstance(events, list):
        for event in events[:30]:
            evt = {
                "type": event.get("type", ""),
                "repo": event.get("repo", {}).get("name", ""),
                "created_at": event.get("created_at", ""),
            }
            payload = event.get("payload", {})
            if event["type"] == "PushEvent":
                commits = payload.get("commits", [])
                evt["commits"] = [c.get("message", "").split("\n")[0] for c in commits[:3]]
            elif event["type"] == "PullRequestEvent":
                pr = payload.get("pull_request", {})
                evt["title"] = pr.get("title", "")
                evt["action"] = payload.get("action", "")
                evt["url"] = pr.get("html_url", "")
            elif event["type"] == "IssueCommentEvent":
                evt["body_preview"] = payload.get("comment", {}).get("body", "")[:100]
                evt["issue_title"] = payload.get("issue", {}).get("title", "")
            elif event["type"] == "PullRequestReviewEvent":
                evt["pr_title"] = payload.get("pull_request", {}).get("title", "")
                evt["review_state"] = payload.get("review", {}).get("state", "")
            recent_events.append(evt)

    contrib = user.get("contributionsCollection", {})
    return {
        "stats": {
            "total_contributions_ytd": contrib.get("contributionCalendar", {}).get("totalContributions", 0),
            "commits_ytd": contrib.get("totalCommitContributions", 0),
            "prs_ytd": contrib.get("totalPullRequestContributions", 0),
            "reviews_ytd": contrib.get("totalPullRequestReviewContributions", 0),
            "issues_ytd": contrib.get("totalIssueContributions", 0),
        },
        "recent_prs": [
            {
                "title": pr.get("title", ""),
                "url": pr.get("url", ""),
                "state": pr.get("state", ""),
                "repo": pr.get("repository", {}).get("nameWithOwner", ""),
                "updated": pr.get("updatedAt", ""),
            }
            for pr in user.get("pullRequests", {}).get("nodes", [])
        ],
        "contributed_repos": [
            {
                "name": r.get("nameWithOwner", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
                "language": (r.get("primaryLanguage") or {}).get("name", ""),
            }
            for r in user.get("repositoriesContributedTo", {}).get("nodes", [])
        ],
        "own_repos": [
            {
                "name": r.get("name", ""),
                "full_name": f"{GITHUB_USERNAME}/{r.get('name', '')}",
                "url": r.get("url", ""),
                "description": r.get("description", ""),
                "language": (r.get("primaryLanguage") or {}).get("name", ""),
                "stars": r.get("stargazerCount", 0),
                "pushed_at": r.get("pushedAt", ""),
            }
            for r in user.get("repositories", {}).get("nodes", [])
        ],
        "recent_events": recent_events,
        "contribution_calendar": contrib.get("contributionCalendar", {}),
    }


def fetch_substack_posts() -> list[dict]:
    """Fetch latest posts from Substack RSS feed."""
    try:
        req = urllib.request.Request(SUBSTACK_RSS, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode()
    except Exception as e:
        print(f"Substack RSS error: {e}")
        return []

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        print(f"Substack RSS parse error: {e}")
        return []

    posts = []
    channel = root.find("channel")
    if channel is None:
        return posts

    for item in channel.findall("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        description = item.findtext("description", "")
        clean_desc = re.sub(r"<[^>]+>", "", description)[:200]

        # Try to extract categories/tags
        categories = [cat.text for cat in item.findall("category") if cat.text]

        posts.append({
            "title": title,
            "url": link,
            "published": pub_date,
            "summary": clean_desc.strip(),
            "tags": categories,
        })

    return posts[:10]  # Last 10 posts


def load_linkedin_data() -> dict:
    """Load LinkedIn data from local JSON config."""
    path = Path(LINKEDIN_DATA_PATH)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"LinkedIn data load error: {e}")
        return {}


def fetch_all() -> dict:
    """Aggregate all data sources."""
    print("Fetching GitHub activity...")
    github = fetch_github_activity()

    print("Fetching Substack posts...")
    substack_all = fetch_substack_posts()

    print("Loading LinkedIn data...")
    linkedin = load_linkedin_data()

    pinned = linkedin.get("featured_articles", [])
    seen_urls: set[str] = set()
    merged_substack: list[dict] = []
    for post in pinned + filter_professional_posts(substack_all):
        url = post.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged_substack.append(post)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "github_username": GITHUB_USERNAME,
        "github": github,
        "substack": merged_substack,
        "linkedin": linkedin,
    }


def write_last_sync(data: dict) -> None:
    """Write a tracked sync marker so daily runs always produce a commit."""
    github = data.get("github", {})
    stats = github.get("stats", {})
    sync = {
        "synced_at": data.get("generated_at"),
        "github_username": data.get("github_username"),
        "contributions_ytd": stats.get("total_contributions_ytd", 0),
        "substack_posts": len(data.get("substack", [])),
        "featured_repos": len(data.get("linkedin", {}).get("featured_repos", [])),
    }
    sync_path = Path("data/last_sync.json")
    sync_path.parent.mkdir(exist_ok=True)
    sync_path.write_text(json.dumps(sync, indent=2) + "\n")
    print(f"Sync marker written to {sync_path}")


if __name__ == "__main__":
    data = fetch_all()
    out_path = Path("data/activity.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2))
    print(f"Activity data written to {out_path}")
    write_last_sync(data)
