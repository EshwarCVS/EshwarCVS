"""
Generate GitHub profile README.md from aggregated activity data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


MAX_RECENT_REPOS = 3
MAX_FEATURED_REPOS = 3
MAX_ACTIVITY_REPOS = 3

DEFAULT_EXCLUDED_REPOS = {
    "eshwarcvs/eshwarcvs",
    "eshwarcvs/eshwarcvs.github.io",
}

ACCENT = "3949AB"

SKILL_SHIELDS = [
    ("Python", "3776AB", "python"),
    ("Java", "007396", "java"),
    ("Scala", "DC322F", "scala"),
    ("Spark", "E25A1C", "apachespark"),
    ("Kafka", "231F20", "apachekafka"),
    ("Docker", "2496ED", "docker"),
    ("AWS", "232F3E", "amazonaws"),
    ("GraphQL", "E10098", "graphql"),
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


def truncate(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


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
    return ",".join(sorted({full.split("/")[-1] for full in excluded if "/" in full}))


def skill_shield_row() -> str:
    badges = []
    for label, color, logo in SKILL_SHIELDS:
        badges.append(
            f"![{label}](https://img.shields.io/badge/{label.replace(' ', '%20')}-{color}"
            f"?style=flat-square&logo={logo}&logoColor=white)"
        )
    return " ".join(badges)


def visitor_counter(username: str) -> str:
    return (
        f"https://komarev.com/ghpvc/?username={quote(username)}"
        f"&label=Profile+views&color={ACCENT}&style=flat-square"
    )


def github_stats_markdown(username: str, excluded: set[str]) -> str:
    """GitHub readme stats card — lowercase username matches GitHub's canonical handle."""
    hide = hide_repo_param(excluded)
    url = (
        "https://github-readme-stats.vercel.app/api"
        f"?username={quote(username.lower())}"
        "&show_icons=true&hide_border=true&include_all_commits=true"
        f"&hide={hide}"
    )
    return f'<img src="{url}" alt="GitHub stats" width="100%"/>'


def streak_stats_markdown(username: str) -> str:
    url = (
        "https://streak-stats.demolab.com"
        f"?user={quote(username.lower())}&theme=dark&hide_border=true"
        f"&background=0D1117&ring={ACCENT}&fire={ACCENT}&currStreakLabel={ACCENT}"
    )
    return f'<img src="{url}" alt="GitHub streak" width="100%"/>'


def header_section(profile: dict, github_user: str, widgets: dict) -> str:
    intro_name = profile.get("intro_name", "Eshwar Thedla")
    title = profile.get("title", "Software Engineer III")
    company = profile.get("company", "Walmart Global Tech")
    email = profile.get("email", "thedlaeshwar@gmail.com")
    linkedin_url = profile.get("linkedin", "https://linkedin.com/in/eshwarchandravidhyasagar")

    visitor = (
        f'\n\n![Profile views]({visitor_counter(github_user)})'
        if widgets.get("visitor_counter", True)
        else ""
    )
    email_badge = email.replace("@", "%40")

    return f"""<h2>Hi, {intro_name} here</h2>

<img align="right" src="https://media.giphy.com/media/qgQUggAC3Pfv687qPC/giphy.gif?cid=790b7611yp0jiunk7v8tqhv65lyfs6218cr3ywi8tmttpjl5&ep=v1_gifs_search&rid=giphy.gif&ct=g" width="200">

<p><em>{title} at {company} <img src="https://media.giphy.com/media/WUlplcMpOCEmTGBtBW/giphy.gif" width="30"></em></p>

[![Gmail](https://img.shields.io/badge/Gmail-{email_badge}-D14836?style=flat-square&logo=gmail&logoColor=white)]({linkedin_url})
[![LinkedIn](https://img.shields.io/badge/LinkedIn-eshwar-0A66C2?style=flat-square&logo=linkedin&logoColor=white)]({linkedin_url})
[![GitHub followers](https://img.shields.io/github/followers/{github_user.lower()}?label=follow&style=social)](https://github.com/{github_user}){visitor}
"""


def experience_section(linkedin: dict) -> str:
    experience = linkedin.get("experience", [])[:3]
    if not experience:
        return ""

    lines = ["\n---\n\n## 💼 Experience\n"]
    for exp in experience:
        role = exp.get("role", "")
        company = exp.get("company", "")
        period = exp.get("period", "")
        lines.append(f"**{role}** · {company} · {period}  ")

    papers = linkedin.get("papers", [])
    if papers:
        lines.append("\n### 📄 Publications\n")
        for paper in papers:
            title = paper.get("title", "")
            url = paper.get("url", "")
            venue = paper.get("venue", "")
            year = paper.get("year", "")
            link = f"[{title}]({url})" if url else title
            lines.append(f"- {link} — *{venue}* ({year})" if year else f"- {link} — *{venue}*")

    skills = linkedin.get("skills", [])
    if skills:
        lines.append(f"\n### 🧰 Stack\n\n{skill_shield_row()}\n")

    return "\n".join(lines)


def featured_projects_section(featured_repos: list[dict]) -> str:
    if not featured_repos:
        return ""

    lines = ["\n---\n\n## 🚀 Featured Projects\n"]
    for repo in featured_repos:
        name = repo.get("name", "")
        url = repo.get("url", "")
        org = repo.get("org", "")
        lang = repo.get("language", "")
        desc = truncate(repo.get("description", ""), 160)
        highlight = truncate(repo.get("highlight", ""), 100)
        npm_pkg = repo.get("npm")

        lang_badge = ""
        if lang:
            color = {"Python": "3776AB", "JavaScript": "F7DF1E", "Java": "007396"}.get(lang, "555555")
            lang_badge = (
                f' <img src="https://img.shields.io/badge/{lang.replace(" ", "%20")}-{color}'
                f'?style=flat-square" alt="{lang}"/>'
            )
        npm_badge = ""
        if npm_pkg:
            npm_badge = (
                f' <a href="https://www.npmjs.com/package/{npm_pkg}">'
                f'<img src="https://img.shields.io/npm/v/{npm_pkg}?style=flat-square&logo=npm&label=npm" alt="npm"/></a>'
            )

        lines.append(
            f'<table>\n<tr>\n<td width="100%">\n'
            f'<b><a href="{url}">{name}</a></b>{lang_badge}{npm_badge}<br/>\n'
            f'<sub>{org}</sub><br/><br/>\n'
            f'{desc}'
        )
        if highlight and highlight.lower() not in desc.lower():
            lines.append(f"<br/><br/><i>{highlight}</i>")
        lines.append("</td>\n</tr>\n</table>\n")
    return "\n".join(lines)


def recent_activity_repos(events: list, excluded: set[str]) -> str:
    """Up to 3 unique repos from recent events — repo name only."""
    repos: list[str] = []
    seen_names: set[str] = set()

    for evt in events:
        repo_full = evt.get("repo", "")
        if not repo_full or is_excluded_repo(repo_full, excluded):
            continue
        name = repo_full.split("/")[-1].lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        repos.append(f"- [{repo_full.split('/')[-1]}](https://github.com/{repo_full})")
        if len(repos) >= MAX_ACTIVITY_REPOS:
            break

    if not repos:
        return ""

    return "\n---\n\n## ⚡ Recent Activity\n\n" + "\n".join(repos) + "\n"


def contributions_section(
    github_user: str,
    widgets: dict,
    excluded: set[str],
    stats: dict,
    year: int,
) -> str:
    parts = ["\n---\n\n## 📊 GitHub Contributions\n\n<div align=\"center\">\n\n"]

    ytd = stats.get("total_contributions_ytd", 0)
    commits = stats.get("commits_ytd", 0)
    prs = stats.get("prs_ytd", 0)
    reviews = stats.get("reviews_ytd", 0)

    parts.append(
        f"![{year} contributions](https://img.shields.io/badge/{year}%20contributions-{ytd}-brightgreen?style=flat-square) "
        f"![Commits](https://img.shields.io/badge/commits-{commits}-blue?style=flat-square) "
        f"![PRs](https://img.shields.io/badge/PRs-{prs}-purple?style=flat-square) "
        f"![Reviews](https://img.shields.io/badge/reviews-{reviews}-orange?style=flat-square)\n\n"
    )

    if widgets.get("github_stats", True):
        parts.append(github_stats_markdown(github_user, excluded) + "\n\n")

    if widgets.get("streak_stats", True):
        parts.append(streak_stats_markdown(github_user) + "\n\n")

    parts.append("</div>")
    return "".join(parts)


def technical_writing_section(linkedin: dict, substack: list) -> str:
    journal = linkedin.get("learning_journal", {})
    lines = ["\n---\n\n## ✍️ Technical Writing\n"]

    if journal:
        name = journal.get("name", "vigilant-lamp")
        url = journal.get("url", "")
        desc = journal.get("description", "Technical learning journal")
        lines.append(f"- **Learn what I learn:** [{name}]({url}) — {desc}")

    for post in substack[:3]:
        title = post.get("title", "")
        url = post.get("url", "")
        date = format_date(post.get("published", "")) or post.get("published", "")
        lines.append(f"- [{title}]({url}) · {date}")

    if len(lines) == 1:
        return ""
    return "\n".join(lines) + "\n"


def star_cta_section(github_user: str, featured_repos: list[dict]) -> str:
    if not featured_repos:
        return ""
    badges = [
        f"[![Star profile](https://img.shields.io/github/stars/{github_user}/{github_user}"
        f"?style=social&label=Star+profile)](https://github.com/{github_user}/{github_user})",
    ]
    for repo in featured_repos[:2]:
        org, name = repo.get("org", ""), repo.get("name", "")
        if org and name:
            badges.append(
                f"[![{name}](https://img.shields.io/github/stars/{org}/{name}"
                f"?style=social&label={name})]({repo.get('url', '')})"
            )
        npm_pkg = repo.get("npm")
        if npm_pkg:
            badges.append(
                f"[![npm](https://img.shields.io/npm/dm/{npm_pkg}?style=flat-square&logo=npm&label=npm)]"
                f"(https://www.npmjs.com/package/{npm_pkg})"
            )

    return (
        "\n---\n\n<div align=\"center\">\n\n"
        + " ".join(badges)
        + "\n\n</div>\n"
    )


def community_section(community: list) -> str:
    if not community:
        return ""
    lines = ["\n---\n\n## 🤝 Community\n"]
    for item in community:
        title = item.get("title", "")
        url = item.get("url", "")
        desc = item.get("description", "")
        cta = item.get("cta", "")
        period = item.get("period", "")
        period_str = f" *({period})*" if period else ""
        lines.append(f"**[{title}]({url})**{period_str}  ")
        lines.append(f"{desc}  ")
        if cta:
            lines.append(f"{cta}  ")
        lines.append("")
    return "\n".join(lines)


def generate_readme(data: dict) -> str:
    now = datetime.now(timezone.utc)
    github = data.get("github", {})
    linkedin = data.get("linkedin", {})
    profile = linkedin.get("profile", {})
    widgets = linkedin.get("readme_widgets", {})
    github_user = data.get("github_username") or profile.get("github_username", "EshwarCVS")
    substack = data.get("substack", [])
    stats = github.get("stats", {})
    excluded = excluded_repo_names(linkedin)

    featured_repos = sorted(
        linkedin.get("featured_repos", []),
        key=lambda r: r.get("priority", 99),
    )[:MAX_FEATURED_REPOS]
    featured_urls = featured_repo_urls(linkedin)

    sections = [
        header_section(profile, github_user, widgets),
        experience_section(linkedin),
        contributions_section(github_user, widgets, excluded, stats, now.year),
        featured_projects_section(featured_repos),
        recent_activity_repos(github.get("recent_events", []), excluded),
    ]

    # Recently updated (compact)
    own_repos = github.get("own_repos", [])
    recent = [
        r for r in own_repos
        if r.get("url", "").rstrip("/") not in featured_urls
        and not is_excluded_repo(r.get("full_name") or r.get("name", ""), excluded)
    ]
    if recent:
        lines = ["\n---\n\n## 🕐 Recently Updated\n"]
        for repo in recent[:MAX_RECENT_REPOS]:
            name = repo.get("full_name") or repo.get("name", "")
            url = repo.get("url", "")
            lang = repo.get("language", "") or "—"
            lines.append(f"- [{name}]({url}) · `{lang}`")
        sections.append("\n".join(lines) + "\n")

    sections.append(community_section(linkedin.get("community", [])))
    sections.append(technical_writing_section(linkedin, substack))

    interests = linkedin.get("interests", [])
    if interests:
        lines = ["\n---\n\n## 🎯 Beyond Code\n"]
        for item in interests:
            label = item.get("label", "")
            url = item.get("url", "")
            desc = item.get("description", "")
            icon = item.get("icon", "")
            link = f"[{label}]({url})" if url else label
            lines.append(f"- {icon} **{link}** — {desc}")
        sections.append("\n".join(lines) + "\n")

    if widgets.get("star_cta", True):
        sections.append(star_cta_section(github_user, featured_repos))

    sections.append(
        f"\n---\n\n<sub>Auto-updated {now.strftime('%b %d, %Y %H:%M UTC')}</sub>\n"
    )

    return "\n".join(s for s in sections if s)


if __name__ == "__main__":
    data_path = Path("data/activity.json")
    linkedin_path = Path("data/linkedin.json")

    if data_path.exists():
        data = json.loads(data_path.read_text())
    else:
        data = {"github": {}, "substack": [], "github_username": "EshwarCVS"}

    if linkedin_path.exists():
        data["linkedin"] = json.loads(linkedin_path.read_text())

    Path("README.md").write_text(generate_readme(data))
    print("README.md generated successfully.")
