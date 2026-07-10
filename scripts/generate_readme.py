"""
Generate GitHub profile README.md from aggregated activity data.

Patterns & tools from:
https://github.com/abhisheknaiidu/awesome-github-profile-readme
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


MAX_ACTIVITY_ITEMS = 5
MAX_FEATURED_REPOS = 3
MAX_RECENT_REPOS = 3

DEFAULT_EXCLUDED_REPOS = {
    "eshwarcvs/eshwarcvs",
    "eshwarcvs/eshwarcvs.github.io",
}

ACCENT = "3949AB"
BG = "0D1117"

TECH_ICONS = [
    ("python", "Python"),
    ("java", "Java"),
    ("csharp", "C#"),
    ("scala", "Scala"),
    ("javascript", "JavaScript"),
    ("react", "React"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("amazonwebservices", "AWS"),
    ("apachekafka", "Kafka"),
    ("graphql", "GraphQL"),
    ("git", "Git"),
]


def format_date(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
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


def excluded_repo_names(linkedin: dict) -> set[str]:
    names = set(DEFAULT_EXCLUDED_REPOS)
    for full_name in linkedin.get("exclude_repos", []):
        names.add(full_name.lower())
    return names


def is_excluded_repo(full_name: str, excluded: set[str]) -> bool:
    key = (full_name or "").lower()
    if key in excluded:
        return True
    short = key.split("/")[-1] if "/" in key else key
    return short in {"eshwarcvs", "eshwarcvs.github.io"}


def featured_repo_urls(linkedin: dict) -> set[str]:
    return {r.get("url", "").rstrip("/") for r in linkedin.get("featured_repos", []) if r.get("url")}


def hide_repo_param(excluded: set[str]) -> str:
    names = sorted({full.split("/")[-1] for full in excluded if "/" in full})
    return ",".join(names)


def tech_icon_row() -> str:
    icons = []
    for icon, title in TECH_ICONS:
        icons.append(
            f'<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{icon}/{icon}-original.svg" '
            f'width="40" height="40" alt="{title}" title="{title}"/>'
        )
    return " ".join(icons)


# --- awesome-github-profile-readme widget URLs ---

def visitor_counter(username: str) -> str:
    return (
        "https://komarev.com/ghpvc"
        f"/?username={quote(username)}&label=Profile+views&color={ACCENT}&style=for-the-badge"
    )


def github_stats_card(username: str, theme: str, excluded: set[str]) -> str:
    hide = hide_repo_param(excluded)
    return (
        "https://github-readme-stats.vercel.app/api"
        f"?username={quote(username)}&show_icons=true&theme={theme}&hide_border=true"
        f"&bg_color={BG}&title_color={ACCENT}&icon_color={ACCENT}"
        f"&include_all_commits=true&count_private=true&hide={quote(hide)}"
    )


def streak_stats_card(username: str, theme: str) -> str:
    return (
        "https://streak-stats.demolab.com"
        f"?user={quote(username)}&theme={theme}&hide_border=true"
        f"&background={BG}&ring={ACCENT}&fire={ACCENT}&currStreakLabel={ACCENT}"
    )


def top_languages_card(username: str, theme: str, excluded: set[str]) -> str:
    hide = hide_repo_param(excluded)
    return (
        "https://github-readme-stats.vercel.app/api/top-langs"
        f"/?username={quote(username)}&layout=donut-vertical&theme={theme}&hide_border=true"
        f"&bg_color={BG}&title_color={ACCENT}&hide={quote(hide)}&langs_count=6"
    )


def contributor_stats_card(username: str, theme: str) -> str:
    return (
        "https://github-contributor-stats.vercel.app/api"
        f"?username={quote(username)}&limit=5&theme={theme}&combine_all_yearly_contributions=true"
        f"&hide_border=true&bg_color={BG}&title_color={ACCENT}"
    )


def activity_graph_card(username: str) -> str:
    return (
        "https://github-readme-activity-graph.vercel.app/graph"
        f"?username={quote(username)}&bg_color={BG}&color={ACCENT}"
        f"&line={ACCENT}&point=FFFFFF&area=true&hide_border=true&custom_title=Contribution%20Graph"
    )


def trophy_card(username: str) -> str:
    return (
        "https://github-profile-trophy.vercel.app"
        f"/?username={quote(username)}&theme=onedark&no-frame=true&margin-w=8&column=4"
    )


def dev_quote_card(theme: str) -> str:
    return f"https://quotes-github-readme.vercel.app/api?type=horizontal&theme={theme}"


def snake_animation_html(username: str) -> str:
    base = f"https://raw.githubusercontent.com/{username}/{username}/output"
    return f"""<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{base}/github-contribution-grid-snake-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="{base}/github-contribution-grid-snake.svg">
  <img alt="github contribution grid snake animation" src="{base}/github-contribution-grid-snake.svg">
</picture>"""


def format_activity_line(evt: dict, excluded: set[str]) -> str | None:
    """DenverCoder1-style activity lines from GitHub public events."""
    typ = evt.get("type", "")
    repo_full = evt.get("repo", "")
    if is_excluded_repo(repo_full, excluded):
        return None

    repo = repo_full.split("/")[-1] if "/" in repo_full else repo_full
    repo_link = f"[{repo}](https://github.com/{repo_full})"

    if typ == "PushEvent":
        commits = evt.get("commits", [])
        msg = truncate(commits[0], 55) if commits else "pushed changes"
        return f"🔥 Pushed to **{repo_link}** — `{msg}`"
    if typ == "PullRequestEvent":
        action = evt.get("action", "")
        title = truncate(evt.get("title", "PR"), 50)
        url = evt.get("url", "")
        emoji = {"opened": "🔀", "closed": "✅", "merged": "🎉"}.get(action, "🔀")
        link = f"[{title}]({url})" if url else title
        return f"{emoji} {action.title()} PR {link} in **{repo_link}**"
    if typ == "PullRequestReviewEvent":
        state = evt.get("review_state", "reviewed")
        title = truncate(evt.get("pr_title", "PR"), 50)
        return f"👀 {state} review on **{title}** in **{repo_link}**"
    if typ == "IssuesEvent":
        return f"🐛 Issue activity in **{repo_link}**"
    if typ == "IssueCommentEvent":
        issue = truncate(evt.get("issue_title", "issue"), 40)
        return f"💬 Commented on **{issue}** in **{repo_link}**"
    if typ == "CreateEvent":
        return f"✨ Created repo **{repo_link}**"
    if typ == "WatchEvent":
        return f"⭐ Starred **{repo_link}**"
    return None


def build_activity_section(events: list, excluded: set[str]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for evt in events:
        line = format_activity_line(evt, excluded)
        if not line:
            continue
        # Dedupe: one line per repo per session
        repo_key = evt.get("repo", "")
        dedupe_key = f"{evt.get('type')}:{repo_key}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        lines.append(line)
        if len(lines) >= MAX_ACTIVITY_ITEMS:
            break
    if not lines:
        return ""
    numbered = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))
    return f"""
---

### ⚡ Recent GitHub Activity

{numbered}
"""


def analytics_section(username: str, widgets: dict, excluded: set[str]) -> str:
    theme = widgets.get("theme", "radical")
    parts: list[str] = []

    if widgets.get("snake_animation", True):
        parts.append(snake_animation_html(username))

    row1: list[str] = []
    if widgets.get("github_stats", True):
        row1.append(
            f'<img src="{github_stats_card(username, theme, excluded)}" height="165" alt="GitHub stats"/>'
        )
    if widgets.get("streak_stats", True):
        row1.append(
            f'<img src="{streak_stats_card(username, theme)}" height="165" alt="GitHub streak"/>'
        )
    if row1:
        parts.append("<br/>\n\n" + " ".join(row1))

    if widgets.get("activity_graph", True):
        parts.append(
            f'\n<br/>\n\n<img src="{activity_graph_card(username)}" width="100%" alt="Activity graph"/>'
        )

    row2: list[str] = []
    if widgets.get("top_languages", True):
        row2.append(
            f'<img src="{top_languages_card(username, theme, excluded)}" height="200" alt="Top languages"/>'
        )
    if widgets.get("contributor_stats", True):
        row2.append(
            f'<img src="{contributor_stats_card(username, theme)}" height="200" alt="Contributor stats"/>'
        )
    if row2:
        parts.append("\n<br/>\n\n" + " ".join(row2))

    if widgets.get("trophies", True):
        parts.append(
            f'\n<br/>\n\n<img src="{trophy_card(username)}" width="100%" alt="GitHub trophies"/>'
        )

    if not parts:
        return ""

    return (
        "\n---\n\n<div align=\"center\">\n\n"
        + "\n\n".join(parts)
        + "\n\n</div>"
    )


def star_cta_section(github_user: str, featured_repos: list[dict]) -> str:
    badges = [
        f"[![Profile stars](https://img.shields.io/github/stars/{github_user}/{github_user}"
        f"?style=for-the-badge&logo=github&label=Star+this+profile&color={ACCENT})]"
        f"(https://github.com/{github_user}/{github_user})",
    ]
    for repo in featured_repos[:2]:
        org = repo.get("org", github_user)
        name = repo.get("name", "")
        if not name:
            continue
        badges.append(
            f"[![{name} stars](https://img.shields.io/github/stars/{org}/{name}"
            f"?style=for-the-badge&logo=github&label={name}&color=181717)]"
            f"({repo.get('url', '')})"
        )
        npm_pkg = repo.get("npm")
        if npm_pkg:
            badges.append(
                f"[![npm downloads](https://img.shields.io/npm/dm/{npm_pkg}"
                f"?style=for-the-badge&logo=npm&label=npm+downloads)]"
                f"(https://www.npmjs.com/package/{npm_pkg})"
            )
    return f"""
---

<div align="center">

### ⭐ Support Open Source

If my work helps you, a star goes a long way!

<br/>

{" ".join(badges)}

</div>
"""


def featured_projects_section(featured_repos: list[dict]) -> str:
    if not featured_repos:
        return ""
    lines = [
        "\n---\n\n### 🚀 Featured Projects\n",
        "<table>",
    ]
    for repo in featured_repos:
        name = repo.get("name", "")
        url = repo.get("url", "")
        org = repo.get("org", "")
        lang = repo.get("language", "")
        desc = truncate(repo.get("description", ""), 100)
        highlight = repo.get("highlight", "")
        lang_shield = (
            f"![{lang}](https://img.shields.io/badge/{lang.replace(' ', '%20')}-{ACCENT}"
            f"?style=flat-square&logoColor=white)"
            if lang else ""
        )
        star_shield = (
            f"![stars](https://img.shields.io/github/stars/{org}/{name}"
            f"?style=flat-square&label=stars&color=181717)"
            if org and name else ""
        )
        lines.append(f"""<tr>
<td width="55">🔷</td>
<td>
<b><a href="{url}">{name}</a></b> · <code>{org}</code> {lang_shield} {star_shield}<br/>
<sub>{desc}</sub>
{f'<br/><sub>✨ {truncate(highlight, 90)}</sub>' if highlight else ''}
</td>
</tr>""")
    lines.append("</table>")
    return "\n".join(lines)


def generate_readme(data: dict) -> str:
    now = datetime.now(timezone.utc)
    github = data.get("github", {})
    linkedin = data.get("linkedin", {})
    profile = linkedin.get("profile", {})
    widgets = linkedin.get("readme_widgets", {})
    github_user = data.get("github_username") or profile.get("github_username", "EshwarCVS")
    substack = data.get("substack", [])
    excluded = excluded_repo_names(linkedin)

    name = profile.get("name", "Eshwar Chandra Vidhyasagar")
    title = profile.get("title", "Software Engineer III")
    company = profile.get("company", "Walmart Global Tech")
    email = profile.get("email", "thedlaeshwar@gmail.com")
    linkedin_url = profile.get("linkedin", "https://linkedin.com/in/eshwarchandravidhyasagar")
    website = profile.get("website", "https://eshwarcvs.github.io")
    substack_url = profile.get("substack", "https://devdine.substack.com")

    featured_repos = sorted(
        linkedin.get("featured_repos", []),
        key=lambda r: r.get("priority", 99),
    )[:MAX_FEATURED_REPOS]
    featured_urls = featured_repo_urls(linkedin)

    sections: list[str] = []

    # Header
    sections.append(f"""<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a237e,50:283593,100:3949ab&height=165&section=header&text={name.replace(' ', '%20')}&fontSize=36&fontColor=fff&animation=fadeIn&fontAlignY=40&desc={title.replace(' ', '%20')}%20%40%20{company.replace(' ', '%20')}&descSize=17&descAlignY=60&descAlign=55"/>

<br/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=22&pause=1000&color=3949AB&center=true&vCenter=true&width=620&lines=Building+scalable+microservices;Open+source+%26+DevSecOps;Community+contributor" alt="Typing SVG" />

<br/><br/>

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)]({linkedin_url})
[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:{email})
[![Substack](https://img.shields.io/badge/Substack-FF6719?style=for-the-badge&logo=substack&logoColor=white)]({substack_url})
[![Website](https://img.shields.io/badge/Portfolio-000000?style=for-the-badge&logo=githubpages&logoColor=white)]({website})

<br/>

{f'![Profile views]({visitor_counter(github_user)})' if widgets.get('visitor_counter', True) else ''}

<br/>

{tech_icon_row()}

</div>""")

    # Analytics block (snake, stats, graph, trophies)
    analytics = analytics_section(github_user, widgets, excluded)
    if analytics:
        sections.append(analytics)

    # Star CTAs — drives stars on OSS + profile repo
    if widgets.get("star_cta", True) and featured_repos:
        sections.append(star_cta_section(github_user, featured_repos))

    # Rich activity feed (DenverCoder1 pattern)
    activity = build_activity_section(github.get("recent_events", []), excluded)
    if activity:
        sections.append(activity)

    # Featured projects
    sections.append(featured_projects_section(featured_repos))

    # Recently updated
    own_repos = github.get("own_repos", [])
    recent_repos = [
        r for r in own_repos
        if r.get("url", "").rstrip("/") not in featured_urls
        and not is_excluded_repo(r.get("full_name") or r.get("name", ""), excluded)
    ]
    if recent_repos:
        sections.append("""
---

### 🕐 Recently Updated

| Repo | Lang | ⭐ | Updated |
|:---|:---:|:---:|:---|
""")
        for repo in recent_repos[:MAX_RECENT_REPOS]:
            name_r = repo.get("full_name") or repo.get("name", "")
            url = repo.get("url", "")
            lang = repo.get("language", "") or "—"
            stars = repo.get("stars", 0)
            pushed = format_date(repo.get("pushed_at", "")) or "—"
            sections.append(f"| [{name_r}]({url}) | `{lang}` | {stars} | {pushed} |\n")

    # Experience + publications
    if linkedin:
        sections.append("""
---

### 💼 Experience
""")
        for exp in linkedin.get("experience", [])[:3]:
            sections.append(
                f"- 🏢 **{exp.get('role', '')}** · `{exp.get('company', '')}` · *{exp.get('period', '')}*"
            )

        papers = linkedin.get("papers", [])
        if papers:
            sections.append("\n**📄 Publications**\n")
            for paper in papers:
                title_p = paper.get("title", "")
                url = paper.get("url", "")
                venue = paper.get("venue", "")
                year = paper.get("year", "")
                year_str = f" ({year})" if year else ""
                link = f"[{title_p}]({url})" if url else title_p
                sections.append(f"- 📑 {link} — *{venue}*{year_str}")

    # Community
    community = linkedin.get("community", [])
    if community:
        sections.append("""
---

### 🤝 Community

<table>
""")
        for item in community:
            icon = item.get("icon", "🤝")
            title_c = item.get("title", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            cta = item.get("cta", "")
            period = item.get("period", "")
            period_str = f" · *{period}*" if period else ""
            sections.append(f"""<tr>
<td width="50">{icon}</td>
<td>
<b><a href="{url}">{title_c}</a></b>{period_str}<br/>
{desc}
{f'<br/><br/>{cta}' if cta else ''}
</td>
</tr>""")
        sections.append("</table>")

    # Technical writing
    if substack:
        sections.append("\n---\n\n### ✍️ Technical Writing\n")
        for post in substack[:3]:
            title_p = post.get("title", "")
            url = post.get("url", "")
            date = format_date(post.get("published", "")) or post.get("published", "")
            sections.append(f"- 📝 [{title_p}]({url}) · `{date}`")

    sections.append("""
---

### 📚 Learn What I Learn

<div align="center">

[![Learning Journal](https://img.shields.io/badge/📓_vigilant--lamp-Learning_Journal-3949AB?style=for-the-badge)](https://github.com/EshwarCVS/vigilant-lamp)

</div>
""")

    # Interests
    interests = linkedin.get("interests", [])
    if interests:
        sections.append("""
---

### 🎯 Beyond Code

| | Interest | About |
|:---:|:---|:---|
""")
        for item in interests:
            icon = item.get("icon", "✨")
            label = item.get("label", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            label_cell = f"**[{label}]({url})**" if url else f"**{label}**"
            sections.append(f"| {icon} | {label_cell} | {desc} |\n")

    # Dev quote
    if widgets.get("dev_quotes", True):
        theme = widgets.get("theme", "radical")
        sections.append(f"""
---

<div align="center">

<img src="{dev_quote_card(theme)}" alt="Dev quote"/>

</div>
""")

    # Footer
    sections.append(f"""
---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3949ab,100:1a237e&height=90&section=footer&text=Thanks%20for%20visiting!&fontSize=22&fontColor=fff&animation=fadeIn" />

<br/>

*🤖 Auto-updated {now.strftime('%b %d, %Y at %H:%M UTC')} · [GitHub Actions](https://github.com/EshwarCVS/EshwarCVS/actions)*

<sub>Built with tools from <a href="https://github.com/abhisheknaiidu/awesome-github-profile-readme">awesome-github-profile-readme</a></sub>

</div>
""")

    return "\n".join(sections)


if __name__ == "__main__":
    data_path = Path("data/activity.json")
    linkedin_path = Path("data/linkedin.json")

    if data_path.exists():
        data = json.loads(data_path.read_text())
    else:
        data = {"github": {}, "substack": [], "github_username": "EshwarCVS"}

    if linkedin_path.exists():
        data["linkedin"] = json.loads(linkedin_path.read_text())

    readme = generate_readme(data)
    Path("README.md").write_text(readme)
    print("README.md generated successfully.")
