"""
Generate GitHub profile README.md from aggregated activity data.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path


MAX_RECENT_PUSH_REPOS = 3
MAX_FEATURED_REPOS = 3
MAX_RECENT_REPOS = 3


def format_date(iso_str: str) -> str:
    """Format ISO date to readable string."""
    if not iso_str:
        return ""
    try:
        # Handle RSS date format
        for fmt in [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
        ]:
            try:
                dt = datetime.strptime(iso_str, fmt)
                return dt.strftime("%b %d, %Y")
            except ValueError:
                continue
        return iso_str[:10]
    except Exception:
        return iso_str[:10]


def truncate(text: str, max_len: int = 80) -> str:
    if not text:
        return ""
    return text[:max_len] + ("..." if len(text) > max_len else "")


def featured_repo_urls(linkedin: dict) -> set[str]:
    return {r.get("url", "").rstrip("/") for r in linkedin.get("featured_repos", []) if r.get("url")}


def format_repo_line(
    name: str,
    url: str,
    desc: str,
    lang: str = "",
    org: str = "",
    stars: int = 0,
    pushed_at: str = "",
    bold: bool = False,
) -> str:
    lang_badge = f" `{lang}`" if lang else ""
    org_badge = f" `{org}`" if org else ""
    star_str = f" ⭐{stars}" if stars > 0 else ""
    date_str = ""
    if pushed_at:
        date_str = f" · updated {format_date(pushed_at)}"
    link = f"**[{name}]({url})**" if bold else f"[{name}]({url})"
    return f"- {link}{org_badge}{lang_badge}{star_str}{date_str} — {desc}"


def generate_readme(data: dict) -> str:
    """Generate the full README.md content."""
    now = datetime.now(timezone.utc)
    github = data.get("github", {})
    github_user = data.get("github_username", "EshwarCVS")
    substack = data.get("substack", [])
    linkedin = data.get("linkedin", {})
    stats = github.get("stats", {})

    sections = []

    # Header
    sections.append("""<div align="center">

# Hi, I'm Eshwar Chandra Vidhyasagar 👋

**Software Engineer III** @ Walmart Global Tech

Building scalable microservices · Open source · Community contributor

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/eshwarchandravidhyasagar)
[![Website](https://img.shields.io/badge/Website-eshwarcvs.github.io-green?style=flat-square&logo=github)](https://eshwarcvs.github.io)

</div>""")

    # Contribution Stats
    sections.append(f"""---

## 📊 {now.year} Contributions

| Metric | Count |
|--------|-------|
| 🟢 Total Contributions | **{stats.get('total_contributions_ytd', 0)}** |
| 📝 Commits | **{stats.get('commits_ytd', 0)}** |
| 🔀 Pull Requests | **{stats.get('prs_ytd', 0)}** |
| 👀 Code Reviews | **{stats.get('reviews_ytd', 0)}** |
| 🐛 Issues | **{stats.get('issues_ytd', 0)}** |""")

    # Recent activity — own-repo pushes only (no stars, PRs, forks, or contributions)
    events = github.get("recent_events", [])
    featured_urls = featured_repo_urls(linkedin)
    if events:
        activity_lines = []
        seen_repos: set[str] = set()
        for evt in events:
            if evt.get("type") != "PushEvent":
                continue
            repo_full = evt.get("repo", "")
            if not repo_full.lower().startswith(f"{github_user.lower()}/"):
                continue
            repo = repo_full.split("/")[-1] if "/" in repo_full else repo_full
            if repo in seen_repos:
                continue
            commits = evt.get("commits", [])
            msg = truncate(commits[0], 60) if commits else "pushed changes"
            activity_lines.append(f"- ⚡ **[{repo}](https://github.com/{repo_full})** — {msg}")
            seen_repos.add(repo)
            if len(activity_lines) >= MAX_RECENT_PUSH_REPOS:
                break

        if activity_lines:
            sections.append("\n## ⚡ Recent Activity\n")
            sections.extend(activity_lines)

    # Featured repos — top 3 curated in linkedin.json (ordered by priority)
    featured_repos = sorted(
        linkedin.get("featured_repos", []),
        key=lambda r: r.get("priority", 99),
    )[:MAX_FEATURED_REPOS]
    featured_urls = featured_repo_urls(linkedin)
    if featured_repos:
        sections.append("\n## ⭐ Featured Repositories\n")
        sections.append(
            "_Hand-picked projects — OSS impact, org work ([FasterApiWeb](https://github.com/FasterApiWeb)), "
            "and tools I actively maintain._\n"
        )
        for repo in featured_repos:
            name = repo.get("name", "")
            url = repo.get("url", "")
            desc = truncate(repo.get("description", ""), 100)
            lang = repo.get("language", "")
            org = repo.get("org", "")
            highlight = repo.get("highlight", "")
            line = format_repo_line(name, url, desc, lang=lang, org=org, bold=True)
            sections.append(line)
            if highlight:
                sections.append(f"  > {highlight}")

    # Recently updated repos — live from GitHub API (excludes featured to avoid duplicates)
    own_repos = github.get("own_repos", [])
    recent_repos = [
        r for r in own_repos
        if r.get("url", "").rstrip("/") not in featured_urls
    ]
    if recent_repos:
        sections.append("\n## 🕐 Recently Updated Repositories\n")
        for repo in recent_repos[:MAX_RECENT_REPOS]:
            name = repo.get("full_name") or repo.get("name", "")
            url = repo.get("url", "")
            desc = truncate(repo.get("description", "") or "No description", 80)
            sections.append(
                format_repo_line(
                    name,
                    url,
                    desc,
                    lang=repo.get("language", ""),
                    stars=repo.get("stars", 0),
                    pushed_at=repo.get("pushed_at", ""),
                )
            )

    # LinkedIn / Professional
    if linkedin:
        sections.append("\n## 💼 Professional\n")
        experience = linkedin.get("experience", [])
        for exp in experience[:3]:
            role = exp.get("role", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            sections.append(f"- **{role}** @ {company} ({period})")

        skills = linkedin.get("skills", [])
        if skills:
            sections.append("\n**Key Skills:** " + " · ".join(skills[:10]))

        papers = linkedin.get("papers", [])
        if papers:
            sections.append("\n### 📄 Publications\n")
            for paper in papers:
                title = paper.get("title", "")
                url = paper.get("url", "")
                venue = paper.get("venue", "")
                if url:
                    sections.append(f"- [{title}]({url}) — {venue}")
                else:
                    sections.append(f"- {title} — {venue}")

    # Community — resume reviews, LinkedIn advocacy (curated in linkedin.json)
    community = linkedin.get("community", [])
    if community:
        sections.append("\n## 🤝 Community\n")
        for item in community:
            title = item.get("title", "")
            url = item.get("url", "")
            desc = truncate(item.get("description", ""), 120)
            period = item.get("period", "")
            period_str = f" ({period})" if period else ""
            sections.append(f"- **[{title}]({url})**{period_str} — {desc}")

    # All personal repos (live from GitHub API)
    if own_repos:
        sections.append("\n## 🚀 All Repositories\n")
        for repo in own_repos[:8]:
            name = repo.get("full_name") or repo.get("name", "")
            url = repo.get("url", "")
            desc = truncate(repo.get("description", "") or "No description", 80)
            sections.append(
                format_repo_line(
                    name,
                    url,
                    desc,
                    lang=repo.get("language", ""),
                    stars=repo.get("stars", 0),
                    pushed_at=repo.get("pushed_at", ""),
                )
            )

    # Professional writing (filtered Substack — CS / security / engineering only)
    if substack:
        sections.append("\n## ✍️ Technical Writing\n")
        for post in substack[:5]:
            title = post.get("title", "")
            url = post.get("url", "")
            date = format_date(post.get("published", "")) or post.get("published", "")
            summary = truncate(post.get("summary", ""), 100)
            sections.append(f"- [{title}]({url}) — {date}")
            if summary:
                sections.append(f"  > {summary}")

    # Learn what I learn
    sections.append("""
## 📚 Learn What I Learn

Check out my learning journal: [vigilant-lamp](https://github.com/EshwarCVS/vigilant-lamp)
""")

    # Interests (professional focus; Substack linked at the end)
    interests = linkedin.get("interests", [])
    if interests:
        sections.append("\n## 🎯 Interests\n")
        for item in interests:
            label = item.get("label", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            if url:
                sections.append(f"- **[{label}]({url})** — {desc}")
            else:
                sections.append(f"- **{label}** — {desc}")

    # Footer
    sections.append(f"""---

<div align="center">

*🤖 Auto-updated on {now.strftime('%b %d, %Y at %H:%M UTC')} via [GitHub Actions](https://github.com/EshwarCVS/EshwarCVS/actions)*

</div>
""")

    return "\n".join(sections)


if __name__ == "__main__":
    data_path = Path("data/activity.json")
    if not data_path.exists():
        print("No activity data found. Run fetch_activity.py first.")
        exit(1)

    data = json.loads(data_path.read_text())
    readme = generate_readme(data)
    Path("README.md").write_text(readme)
    print("README.md generated successfully.")
