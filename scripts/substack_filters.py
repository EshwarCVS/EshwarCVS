"""Filter Substack posts for professional / technical content on the GitHub profile."""

from __future__ import annotations

import re

# Titles/summaries matching these are personal (food, book summaries) — hide on GitHub profile.
PERSONAL_PATTERNS = re.compile(
    r"|".join(
        [
            r"\bcurry\b",
            r"\bchicken\b",
            r"\bbiriyani\b",
            r"\bbiryani\b",
            r"\bpaneer\b",
            r"\bpancake\b",
            r"\bshrimp\b",
            r"\bokra\b",
            r"\brecipe\b",
            r"dish variation",
            r"\bsummary\b",
            r"\bhabits\b",
            r"\bpulusu\b",
            r"\bbendakaya\b",
            r"\broyyala\b",
            r"high-protein",
            r"buttermilk power cakes",
        ]
    ),
    re.IGNORECASE,
)

# Boost inclusion when these appear (CS, security, engineering).
PROFESSIONAL_PATTERNS = re.compile(
    r"|".join(
        [
            r"\bai\b",
            r"\bapi\b",
            r"\bsoftware\b",
            r"\bsecurity\b",
            r"\bsecret",
            r"\bagent",
            r"\bprogramming\b",
            r"\bengineering\b",
            r"\bdeveloper\b",
            r"\bopen.?source\b",
            r"\bgithub\b",
            r"\bcursor\b",
            r"\bcopilot\b",
            r"\bdevsecops\b",
            r"\bcode\b",
            r"\bmicroservice",
            r"\bkubernetes\b",
            r"\bkafka\b",
            r"\bresume\b",
            r"\bcareer\b",
            r"\bjob\s*search\b",
            r"\bmachine learning\b",
            r"\bbayesian\b",
            r"\bdata\b",
            r"\bcloud\b",
        ]
    ),
    re.IGNORECASE,
)


def is_professional_substack_post(title: str, summary: str = "", tags: list | None = None) -> bool:
    """Return True if a post belongs on the professional GitHub profile."""
    text = f"{title} {summary} {' '.join(tags or [])}"

    if PERSONAL_PATTERNS.search(text):
        return False

    if PROFESSIONAL_PATTERNS.search(text):
        return True

    # Default: exclude ambiguous posts (food blog legacy on same Substack).
    return False


def filter_professional_posts(posts: list[dict]) -> list[dict]:
    return [
        p
        for p in posts
        if is_professional_substack_post(
            p.get("title", ""),
            p.get("summary", ""),
            p.get("tags"),
        )
    ]
