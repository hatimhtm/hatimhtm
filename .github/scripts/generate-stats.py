"""Regenerate the stats and languages SVG cards from live GitHub data."""

from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

USERNAME = "hatimhtm"
APPS_LIVE = 2
ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"

QUERY = """{
  user(login: "%s") {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        primaryLanguage { name }
      }
    }
  }
}"""


def gh_graphql(query: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-stats-refresh",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body


def fetch_stats() -> dict:
    data = gh_graphql(QUERY % USERNAME)["data"]["user"]
    cc = data["contributionsCollection"]
    repos = data["repositories"]["nodes"]
    return {
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "repo_count": data["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "contributed_to": cc["totalRepositoriesWithContributedCommits"],
        "languages": Counter(
            r["primaryLanguage"]["name"]
            for r in repos
            if r["primaryLanguage"]
        ).most_common(5),
    }


def number_font_size(n: int) -> int:
    """Shrink the number's font-size as digits grow, so it never overflows the
    ~110 px column."""
    digits = len(str(n))
    return {1: 46, 2: 46, 3: 46, 4: 38, 5: 30}.get(digits, 24)


def stats_svg(s: dict) -> str:
    fs_c = number_font_size(s["commits"])
    fs_p = number_font_size(s["prs"])
    fs_r = number_font_size(s["repo_count"])
    fs_s = number_font_size(s["stars"])
    footer = f"/// {s['contributed_to']} REPOS CONTRIBUTED TO · {APPS_LIVE} APPS LIVE ON APP STORE"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 200" width="480" height="200" role="img" aria-label="GitHub Stats">
  <defs>
    <style>
      .h {{ font-family: 'Helvetica Neue', 'Arial Black', Helvetica, Arial, sans-serif; font-weight: 900; }}
      .m {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, 'Courier New', monospace; font-weight: 700; }}
    </style>
  </defs>
  <rect width="480" height="200" fill="#1A1A1A"/>

  <text class="m" x="20" y="32" font-size="13" letter-spacing="4" fill="#FFFDF5">/// GITHUB STATS</text>
  <line x1="20" y1="46" x2="460" y2="46" stroke="#FFFDF5" stroke-opacity="0.15" stroke-width="1"/>

  <text class="h" x="60"  y="115" font-size="{fs_c}" letter-spacing="-2" fill="#CCFF00" text-anchor="middle">{s['commits']}</text>
  <text class="m" x="60"  y="138" font-size="10" letter-spacing="3"  fill="#FFFDF5" text-anchor="middle">COMMITS</text>

  <text class="h" x="180" y="115" font-size="{fs_p}" letter-spacing="-2" fill="#CCFF00" text-anchor="middle">{s['prs']}</text>
  <text class="m" x="180" y="138" font-size="10" letter-spacing="3"  fill="#FFFDF5" text-anchor="middle">PRS</text>

  <text class="h" x="300" y="115" font-size="{fs_r}" letter-spacing="-2" fill="#CCFF00" text-anchor="middle">{s['repo_count']}</text>
  <text class="m" x="300" y="138" font-size="10" letter-spacing="3"  fill="#FFFDF5" text-anchor="middle">REPOS</text>

  <text class="h" x="420" y="115" font-size="{fs_s}" letter-spacing="-2" fill="#CCFF00" text-anchor="middle">{s['stars']}</text>
  <text class="m" x="420" y="138" font-size="10" letter-spacing="3"  fill="#FFFDF5" text-anchor="middle">STARS</text>

  <line x1="20" y1="165" x2="460" y2="165" stroke="#FFFDF5" stroke-opacity="0.15" stroke-width="1"/>
  <text class="m" x="20" y="184" font-size="9" letter-spacing="2" fill="#FFFDF5" fill-opacity="0.55" textLength="440" lengthAdjust="spacingAndGlyphs">{footer}</text>
</svg>
"""


def languages_svg(langs: list[tuple[str, int]]) -> str:
    if not langs:
        return ""
    total = sum(c for _, c in langs)
    y_text = [64, 94, 124, 154, 184]
    y_bar = [70, 100, 130, 160, 190]
    rows: list[str] = []
    for i, (name, count) in enumerate(langs[:5]):
        pct = count / total * 100
        bar_w = max(1, int(440 * count / total))
        rows.append(
            f'  <text class="m" x="20"  y="{y_text[i]}" font-size="11" letter-spacing="2" fill="#FFFDF5">{name.upper()}</text>\n'
            f'  <text class="m" x="460" y="{y_text[i]}" font-size="11" letter-spacing="2" fill="#CCFF00" text-anchor="end">{pct:.1f}%</text>\n'
            f'  <rect x="20" y="{y_bar[i]}" width="440" height="6" fill="#FFFDF5" fill-opacity="0.12"/>\n'
            f'  <rect x="20" y="{y_bar[i]}" width="{bar_w}" height="6" fill="#CCFF00"/>'
        )
    body = "\n".join(rows)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 200" width="480" height="200" role="img" aria-label="Top Languages">
  <defs>
    <style>
      .m {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, 'Courier New', monospace; font-weight: 700; }}
    </style>
  </defs>
  <rect width="480" height="200" fill="#1A1A1A"/>

  <text class="m" x="20" y="32" font-size="13" letter-spacing="4" fill="#FFFDF5">/// TOP LANGUAGES</text>
  <line x1="20" y1="46" x2="460" y2="46" stroke="#FFFDF5" stroke-opacity="0.15" stroke-width="1"/>

{body}
</svg>
"""


def main() -> None:
    s = fetch_stats()
    print(f"Stats: {s}")
    (ASSETS_DIR / "stats-card.svg").write_text(stats_svg(s))
    (ASSETS_DIR / "languages-card.svg").write_text(languages_svg(s["languages"]))
    print(f"Wrote SVGs to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
