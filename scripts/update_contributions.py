#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

LOGIN = os.getenv("GITHUB_LOGIN", "xFrankB")
OUT_DIR = Path(__file__).resolve().parents[1] / "assets"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        months { firstDay name totalWeeks year }
        weeks {
          firstDay
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""

DARK = {
    "bg_start": "#050505",
    "bg_mid": "#141414",
    "bg_end": "#060606",
    "ink": "#f4f4f4",
    "body": "#d3d3d3",
    "muted": "#8f8f8f",
    "grid": "#ffffff",
    "panel_stroke": "#ffffff",
    "cell_stroke": "#2b2b2b",
    "none": "#111111",
    "levels": {
        "FIRST_QUARTILE": "#444444",
        "SECOND_QUARTILE": "#777777",
        "THIRD_QUARTILE": "#b7b7b7",
        "FOURTH_QUARTILE": "#f2f2f2",
    },
}

LIGHT = {
    "bg_start": "#f3f3ef",
    "bg_mid": "#fbfbf8",
    "bg_end": "#e7e7e2",
    "ink": "#151515",
    "body": "#353535",
    "muted": "#686862",
    "grid": "#222222",
    "panel_stroke": "#777771",
    "cell_stroke": "#c3c3bd",
    "none": "#e4e4df",
    "levels": {
        "FIRST_QUARTILE": "#c6c6c0",
        "SECOND_QUARTILE": "#96968f",
        "THIRD_QUARTILE": "#5d5d57",
        "FOURTH_QUARTILE": "#181818",
    },
}


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_calendar() -> dict:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_TOKEN is required")

    now = datetime.now(timezone.utc)
    variables = {
        "login": LOGIN,
        "from": iso(now - timedelta(days=365)),
        "to": iso(now),
    }
    body = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "xFrankB-contribution-calendar",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    try:
        return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"Unexpected GitHub GraphQL response: {payload}") from error


def month_label(month: dict) -> str:
    names = {
        1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
        7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
    }
    try:
        month_number = int(month["firstDay"][5:7])
    except (KeyError, ValueError):
        return str(month.get("name", ""))[:3].upper()
    return names.get(month_number, str(month.get("name", ""))[:3].upper())


def render(calendar: dict, theme: dict, theme_name: str) -> str:
    weeks = calendar.get("weeks", [])
    total = int(calendar.get("totalContributions", 0))
    all_days = [day for week in weeks for day in week.get("contributionDays", [])]
    dates = [day["date"] for day in all_days if day.get("date")]
    start_date = min(dates) if dates else "unknown"
    end_date = max(dates) if dates else "unknown"

    width, height = 1200, 360
    panel_x, panel_y, panel_w, panel_h, radius = 16, 16, 1168, 328, 34
    grid_x, grid_y, step, cell = 70, 142, 20, 13
    month_y = 116
    level_colors = theme["levels"]
    lines: list[str] = []

    lines.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">''')
    lines.append(f"  <title id=\"title\">GitHub contributions — {LOGIN}</title>")
    lines.append(f"  <desc id=\"desc\">Live contribution calendar for {LOGIN}, {total} contributions between {start_date} and {end_date}.</desc>")
    lines.append("  <defs>")
    lines.append(f'''    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{theme['bg_start']}"/><stop offset="0.55" stop-color="{theme['bg_mid']}"/><stop offset="1" stop-color="{theme['bg_end']}"/></linearGradient>''')
    lines.append(f'''    <pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="{theme['grid']}" stroke-opacity=".055"/><circle cx="1" cy="1" r="1" fill="{theme['grid']}" opacity=".12"/></pattern>''')
    lines.append(f'''    <clipPath id="clip"><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}"/></clipPath>''')
    lines.append("  </defs>")
    lines.append("  <rect width=\"1200\" height=\"360\" fill=\"none\"/>")
    lines.append("  <g clip-path=\"url(#clip)\">")
    lines.append(f'''    <rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#bg)"/>''')
    lines.append(f'''    <rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#grid)"/>''')
    lines.append(f'''    <rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="none" stroke="{theme['panel_stroke']}" stroke-opacity=".22"/>''')
    lines.append("    <g font-family=\"monospace\">")
    lines.append(f'''      <text x="58" y="64" fill="{theme['ink']}" opacity=".78" font-size="14" font-weight="600" letter-spacing="3">/ CONTRIBUTIONS / LAST 12 MONTHS</text>''')
    lines.append(f'''      <text x="1142" y="64" text-anchor="end" fill="{theme['ink']}" font-size="22" font-weight="700">{total} <tspan font-size="12" opacity=".72">TOTAL</tspan></text>''')
    lines.append(f'''      <text x="58" y="92" fill="{theme['body']}" opacity=".86" font-size="14">public activity · daily sync · contribution count by day</text>''')

    month_positions: dict[str, int] = {}
    for index, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            if day.get("date"):
                month_positions.setdefault(day["date"][:7], index)
    for month in calendar.get("months", []):
        key = str(month.get("firstDay", ""))[:7]
        if key in month_positions:
            x = grid_x + month_positions[key] * step
            lines.append(f'''      <text x="{x}" y="{month_y}" fill="{theme['muted']}" opacity=".88" font-size="11" font-weight="600" letter-spacing="1">{escape(month_label(month))}</text>''')

    for weekday, label in ((1, "MON"), (3, "WED"), (5, "FRI")):
        y = grid_y + weekday * step + 10
        lines.append(f'''      <text x="32" y="{y}" text-anchor="end" fill="{theme['muted']}" opacity=".8" font-size="10">{label}</text>''')

    for week_index, week in enumerate(weeks):
        x = grid_x + week_index * step
        for day in week.get("contributionDays", []):
            try:
                weekday = int(day.get("weekday", 0))
            except (TypeError, ValueError):
                weekday = 0
            y = grid_y + weekday * step
            level = day.get("contributionLevel", "NONE")
            fill = level_colors.get(level, theme["none"]) if int(day.get("contributionCount", 0)) else theme["none"]
            count = int(day.get("contributionCount", 0))
            date_value = escape(str(day.get("date", "")))
            label = f"{date_value}: {count} contribution" + ("s" if count != 1 else "")
            lines.append(f'''      <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1"><title>{escape(label)}</title></rect>''')

    legend_y = 306
    lines.append(f'''      <text x="58" y="{legend_y + 10}" fill="{theme['muted']}" opacity=".86" font-size="11">LESS</text>''')
    legend_x = 98
    legend_colors = [theme["none"], level_colors["FIRST_QUARTILE"], level_colors["SECOND_QUARTILE"], level_colors["THIRD_QUARTILE"], level_colors["FOURTH_QUARTILE"]]
    for index, fill in enumerate(legend_colors):
        x = legend_x + index * 22
        lines.append(f'''      <rect x="{x}" y="{legend_y}" width="14" height="14" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1"/>''')
    lines.append(f'''      <text x="218" y="{legend_y + 10}" fill="{theme['muted']}" opacity=".86" font-size="11">MORE</text>''')
    lines.append(f'''      <text x="1142" y="{legend_y + 10}" text-anchor="end" fill="{theme['muted']}" opacity=".76" font-size="11">{escape(start_date)} → {escape(end_date)}</text>''')
    lines.append("    </g>")
    lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    calendar = fetch_calendar()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        OUT_DIR / "contributions.svg": render(calendar, DARK, "dark"),
        OUT_DIR / "contributions-light.svg": render(calendar, LIGHT, "light"),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size} bytes)")
    print(f"total contributions: {calendar.get('totalContributions', 0)}")
    print(f"weeks: {len(calendar.get('weeks', []))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise
