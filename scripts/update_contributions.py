#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
LOGIN = os.getenv("GITHUB_LOGIN", "xFrankB")

YEARS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
  }
}
"""

CALENDAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        months { firstDay name totalWeeks year }
        weeks {
          firstDay
          contributionDays { date contributionCount contributionLevel weekday }
        }
      }
    }
  }
}
"""

TECH_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        name
        isFork
        isArchived
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { nodes { name } }
        packageJson: object(expression: "HEAD:package.json") { ... on Blob { text } }
        requirements: object(expression: "HEAD:requirements.txt") { ... on Blob { text } }
        pyproject: object(expression: "HEAD:pyproject.toml") { ... on Blob { text } }
        goMod: object(expression: "HEAD:go.mod") { ... on Blob { text } }
        cargo: object(expression: "HEAD:Cargo.toml") { ... on Blob { text } }
        dockerfile: object(expression: "HEAD:Dockerfile") { ... on Blob { text } }
        pom: object(expression: "HEAD:pom.xml") { ... on Blob { text } }
        workflows: object(expression: "HEAD:.github/workflows") { __typename }
      }
    }
  }
}
"""

DARK = {
    "bg_start": "#050505", "bg_mid": "#141414", "bg_end": "#060606",
    "ink": "#f4f4f4", "body": "#d3d3d3", "muted": "#8f8f8f",
    "grid": "#ffffff", "panel_stroke": "#ffffff", "cell_stroke": "#2b2b2b",
    "none": "#111111",
    "levels": {"FIRST_QUARTILE": "#444444", "SECOND_QUARTILE": "#777777", "THIRD_QUARTILE": "#b7b7b7", "FOURTH_QUARTILE": "#f2f2f2"},
}

LIGHT = {
    "bg_start": "#f3f3ef", "bg_mid": "#fbfbf8", "bg_end": "#e7e7e2",
    "ink": "#151515", "body": "#353535", "muted": "#686862",
    "grid": "#222222", "panel_stroke": "#777771", "cell_stroke": "#c3c3bd",
    "none": "#e4e4df",
    "levels": {"FIRST_QUARTILE": "#c6c6c0", "SECOND_QUARTILE": "#96968f", "THIRD_QUARTILE": "#5d5d57", "FOURTH_QUARTILE": "#181818"},
}

LANG = {
    "en": {
        "title": "/ CONTRIBUTIONS / {year}",
        "total": "TOTAL",
        "subtitle": "public activity · daily sync · contribution count by day",
        "less": "LESS", "more": "MORE",
        "weekdays": {1: "MON", 3: "WED", 5: "FRI"},
        "contribution": "contribution", "contributions": "contributions",
        "desc": "Live contribution history for {login}, {total} contributions between {start} and {end}.",
        "alt": "Live GitHub contribution history for {login}",
        "history_title": "/ CONTRIBUTIONS / HISTORY",
        "history_subtitle": "public activity · annual history · daily detail",
        "year_word": "contributions",
    },
    "es": {
        "title": "/ CONTRIBUCIONES / {year}",
        "total": "TOTAL",
        "subtitle": "actividad pública · sincronización diaria · contribuciones por día",
        "less": "MENOS", "more": "MÁS",
        "weekdays": {1: "LUN", 3: "MIÉ", 5: "VIE"},
        "contribution": "contribución", "contributions": "contribuciones",
        "desc": "Historial de contribuciones de {login}, {total} contribuciones entre {start} y {end}.",
        "alt": "Historial vivo de contribuciones de GitHub de {login}",
        "history_title": "/ CONTRIBUCIONES / HISTORIAL",
        "history_subtitle": "actividad pública · historial anual · detalle diario",
        "year_word": "contribuciones",
    },
}

PANEL_TRANSLATIONS = {
    "/ PROFILE_IDENTITY": "/ IDENTIDAD",
    "TRAINEE • BUILDING IN PUBLIC": "TRAINEE • CONSTRUYENDO EN PÚBLICO",
    "ONLINE • BUILDING IN PUBLIC": "EN LÍNEA • CONSTRUYENDO EN PÚBLICO",
    "FULL-STACK • APPLIED AI • BUILDING": "FULL-STACK • IA APLICADA • CONSTRUYENDO",
    "SOFTWARE • AI • MULTIPLATFORM": "SOFTWARE • IA • MULTIPLATAFORMA",
    "03  AI / DATA": "03  IA / DATOS",
    "04  QUALITY": "04  CALIDAD",
    "/ WHOAMI": "/ QUIÉN_SOY",
    "Software developer trainee focused on full-stack products": "Desarrollador trainee enfocado en productos full-stack",
    "and applied AI: interfaces, architecture, automation": "e IA aplicada: interfaces, arquitectura, automatización",
    "and practical problem solving.": "y resolución práctica de problemas.",
    "$ mission: entender → construir → documentar → mejorar": "$ misión: entender → construir → documentar → mejorar",
    "/ FOCUS": "/ ENFOQUE",
    "03 AI / DATA": "03 IA / DATOS",
    "04 QUALITY": "04 CALIDAD",
    "/ SELECTED_WORK": "/ PROYECTO_CLAVE",
    "Aplicación full-stack modular con límites visibles.": "Aplicación full-stack modular con límites claros.",
    "BUILD_PIPELINE": "CICLO_DE_BUILD",
    "/ CONTACT": "/ CONTACTO",
    "/ PROOF_OF_WORK": "/ PRUEBA_DEL_TRABAJO",
    "Aplicación full-stack organizada para crecer por módulos.": "Aplicación full-stack modular y preparada para crecer.",
    "public repository · main · MIT": "repositorio público · main · MIT",
    "PRIMARY_LANGUAGE": "LENGUAJE_PRINCIPAL",
    "STRUCTURE": "ESTRUCTURA",
    "architecture visible in repository · modular boundaries · reproducible commands": "arquitectura visible en el repo · límites modulares · comandos reproducibles",
    "VERIFIED_SIGNAL / PUBLIC_REPO": "SEÑAL_VERIFICADA / REPO_PÚBLICO",
    "PRIMARY_REPOSITORY": "REPOSITORIO_PRINCIPAL",
    "STACK_DETECTED": "STACK_DETECTADO",
    "BUILD_LOOP": "CICLO_DE_BUILD",
    "format · reproducible commands": "format · comandos reproducibles",
    "END_OF_PROFILE": "FIN_DEL_PERFIL",
    "BUILD • LEARN • REPEAT": "CONSTRUIR • APRENDER • REPETIR",
}


def iso_year(year: int, end: bool = False) -> str:
    suffix = "12-31T23:59:59Z" if end else "01-01T00:00:00Z"
    return f"{year:04d}-{suffix}"


def graphql(query: str, variables: dict) -> dict:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_TOKEN is required")
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "xFrankB-contribution-calendar"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


LANGUAGE_LABELS = {
    "TypeScript": "TypeScript", "JavaScript": "JavaScript", "Python": "Python",
    "CSS": "CSS", "HTML": "HTML", "C++": "C++", "C": "C", "C#": "C#",
    "Java": "Java", "Go": "Go", "Rust": "Rust", "Dart": "Dart",
    "Kotlin": "Kotlin", "Swift": "Swift", "Shell": "Shell",
}

DEPENDENCY_LABELS = {
    "react": "React", "react-dom": "React", "vite": "Vite", "express": "Express",
    "typescript": "TypeScript", "next": "Next.js", "vue": "Vue", "svelte": "Svelte",
    "angular": "Angular", "tailwindcss": "Tailwind CSS", "framer-motion": "Framer Motion",
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django", "numpy": "NumPy",
    "pandas": "Pandas", "torch": "PyTorch", "pytorch": "PyTorch", "scikit-learn": "scikit-learn",
    "matplotlib": "Matplotlib", "axios": "Axios", "zod": "Zod",
}

TECH_PRIORITY = [
    "TypeScript", "JavaScript", "Python", "React", "Vite", "Node.js", "Express",
    "pnpm", "HTML", "CSS", "Tailwind CSS", "FastAPI", "Flask", "Django", "NumPy",
    "Pandas", "PyTorch", "Git", "GitHub Actions", "Linux", "Docker", "Go", "Rust",
]
TECH_FALLBACK = ["TypeScript", "JavaScript", "Python", "React", "Vite", "Node.js", "Express", "pnpm", "Git", "Linux", "HTML", "CSS"]
TECH_ALIASES = {
    "react-dom": "React", "reactjs": "React", "node": "Node.js", "nodejs": "Node.js",
    "npm": "npm", "pnpm": "pnpm", "github-actions": "GitHub Actions",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS", "scikit learn": "scikit-learn",
    "pytorch": "PyTorch", "torch": "PyTorch", "numpy": "NumPy", "pandas": "Pandas",
}

TECH_MARKS = {
    "TypeScript": "TS", "JavaScript": "JS", "Python": "PY", "React": "RE",
    "Vite": "VT", "Node.js": "ND", "Express": "EX", "pnpm": "PN",
    "HTML": "HT", "CSS": "CS", "Tailwind CSS": "TW", "Git": "GI",
    "GitHub Actions": "CI", "Linux": "LX", "Docker": "DK",
}
TECH_ICON_FILES = {
    "TypeScript": "typescript.svg", "JavaScript": "javascript.svg", "Python": "python.svg",
    "React": "react.svg", "Vite": "vite.svg", "Node.js": "nodedotjs.svg", "Express": "express.svg",
    "pnpm": "pnpm.svg", "HTML": "html5.svg", "CSS": "css.svg", "Tailwind CSS": "tailwindcss.svg",
    "Git": "git.svg", "GitHub Actions": "githubactions.svg", "Linux": "linux.svg", "Axios": "axios.svg",
    "Framer Motion": "framer.svg", "Zod": "zod.svg",
}


def canonical_technology(value: str) -> str:
    value = str(value).strip()
    key = re.sub(r"[._/]+", "-", value.lower())
    key = re.sub(r"\s+", " ", key)
    return TECH_ALIASES.get(key, value)


def technology_mark(technology: str) -> str:
    if technology in TECH_MARKS:
        return TECH_MARKS[technology]
    words = re.findall(r"[A-Za-z0-9]+", technology)
    return "".join(word[0] for word in words).upper()[:3] or "•"


def technology_icon_paths(technology: str) -> list[str]:
    filename = TECH_ICON_FILES.get(technology)
    if filename:
        icon = ASSETS / "tech-icons" / filename
        if icon.exists():
            paths = re.findall(r'<path\b[^>]*\bd="([^"]+)"', icon.read_text(encoding="utf-8"))
            if paths:
                return paths
    return ["M12 2.5a9.5 9.5 0 1 0 0 19 9.5 9.5 0 0 0 0-19Zm0 3a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Zm-1.5 3h3v3h-3v-3Zm0 4.5h3v3h-3v-3Z"]


def _add_technology(found: set[str], value: str | None) -> None:
    if not value:
        return
    value = canonical_technology(value)
    if value in LANGUAGE_LABELS or value in DEPENDENCY_LABELS.values() or value in {"Node.js", "pnpm", "Git", "GitHub Actions", "Linux", "Docker", "npm"}:
        found.add(value)


def _scan_package_json(text: str, found: set[str]) -> None:
    try:
        package = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return
    _add_technology(found, "Node.js")
    if str(package.get("packageManager", "")).lower().startswith("pnpm@"):
        _add_technology(found, "pnpm")
    for group in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for dependency in (package.get(group) or {}):
            label = DEPENDENCY_LABELS.get(str(dependency).lower())
            _add_technology(found, label)


def _scan_manifest(text: str, found: set[str]) -> None:
    lowered = (text or "").lower()
    for dependency, label in DEPENDENCY_LABELS.items():
        if re.search(rf"(?<![a-z0-9_-]){re.escape(dependency)}(?![a-z0-9_-])", lowered):
            _add_technology(found, label)


def detected_technologies() -> list[str]:
    data = graphql(TECH_QUERY, {"login": LOGIN})
    found: set[str] = set()
    for repository in data["user"]["repositories"].get("nodes", []):
        if not repository or repository.get("isFork") or repository.get("isArchived"):
            continue
        _add_technology(found, "Git")
        for language in repository.get("languages", {}).get("nodes", []):
            language_name = str(language.get("name", "")).strip()
            if language_name:
                found.add(canonical_technology(LANGUAGE_LABELS.get(language_name, language_name)))
        package_json = repository.get("packageJson") or {}
        _scan_package_json(package_json.get("text", ""), found)
        for field in ("requirements", "pyproject", "goMod", "cargo", "dockerfile", "pom"):
            manifest = repository.get(field) or {}
            _scan_manifest(manifest.get("text", ""), found)
        if repository.get("dockerfile"):
            _add_technology(found, "Docker")
        if (repository.get("workflows") or {}).get("__typename") == "Tree":
            _add_technology(found, "GitHub Actions")
            _add_technology(found, "Linux")
    if not found:
        found.update(TECH_FALLBACK)
    priority = {name: index for index, name in enumerate(TECH_PRIORITY)}
    return sorted(found, key=lambda name: (priority.get(name, 999), name.lower()))


def render_technology_sequence(technologies: list[str]) -> str:
    """Show every unique technology one at a time inside the hero galaxy."""
    technologies = list(dict.fromkeys(technologies)) or TECH_FALLBACK

    count = len(technologies)
    slot = 3.96

    duration = count * slot
    lines = [
        '    <g transform="translate(820 28)" aria-label="Animated technology sequence">',
        '      <ellipse cx="170" cy="132" rx="174" ry="98" transform="rotate(-18 170 132)" fill="none" stroke="#ffffff" stroke-opacity="0.34" stroke-width="1.3" stroke-dasharray="3 12">',
        '        <animate attributeName="stroke-dashoffset" values="0;-120" dur="12s" repeatCount="indefinite"/>',
        '      </ellipse>',
        '      <ellipse cx="170" cy="132" rx="138" ry="68" transform="rotate(18 170 132)" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="1.0" stroke-dasharray="2 10">',
        '        <animate attributeName="stroke-dashoffset" values="0;90" dur="9s" repeatCount="indefinite"/>',
        '      </ellipse>',
        '      <circle cx="170" cy="132" r="80" fill="none" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1"/>',
        '      <circle cx="170" cy="132" r="3" fill="#ffffff" fill-opacity="0.76">',
        '        <animate attributeName="r" values="2;5;2" dur="4s" repeatCount="indefinite"/>',
        '      </circle>',
    ]
    for index, technology in enumerate(technologies):
        label = escape(technology)
        paths = technology_icon_paths(technology)
        start = (index * slot + 0.08) / duration
        fade_in_end = (index * slot + 0.38) / duration
        hold_end = (index * slot + 3.56) / duration
        fade_out_end = (index * slot + 3.88) / duration
        lines.extend([
            '      <g opacity="0">',
            f'        <title>{label} — detected in public repositories</title>',
            '        <circle cx="170" cy="132" r="56" fill="#ffffff" fill-opacity="0.018" stroke="#ffffff" stroke-opacity="0.16" stroke-width="1"/>',
            f'        <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;{start:.5f};{fade_in_end:.5f};{hold_end:.5f};{fade_out_end:.5f}" dur="{duration:.1f}s" begin="0s" repeatCount="indefinite"/>',
            f'        <animate attributeName="display" values="none;inline;inline;none;none" keyTimes="0;{start:.5f};{fade_in_end:.5f};{fade_out_end:.5f};1" dur="{duration:.1f}s" begin="0s" repeatCount="indefinite"/>',
            '        <circle cx="170" cy="132" r="50" fill="#ffffff" fill-opacity="0.045" stroke="#ffffff" stroke-opacity="0.54" stroke-width="1.2">',
            '          <animate attributeName="r" values="48;51;48" dur="3.96s" repeatCount="indefinite"/>',
            '        </circle>',
            '        <svg x="138" y="100" width="64" height="64" viewBox="0 0 24 24" aria-hidden="true">',
            *[f'          <path d="{escape(path)}" fill="#d3d3d3" fill-opacity="0.66"/>' for path in paths],
            '        </svg>',
            '      </g>',
        ])
    lines.append('    </g>')
    return "\n".join(lines)


def update_technology_orbit(technologies: list[str]) -> None:
    source = ASSETS / "hero.svg"
    text = source.read_text(encoding="utf-8")
    pattern = r'    <!-- TECH_ORBIT_START -->.*?    <!-- TECH_ORBIT_END -->'
    replacement = "    <!-- TECH_ORBIT_START -->\n" + render_technology_sequence(technologies) + "\n    <!-- TECH_ORBIT_END -->"
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("TECH_ORBIT markers were not found in assets/hero.svg")
    source.write_text(updated, encoding="utf-8")


def available_years() -> list[int]:
    data = graphql(YEARS_QUERY, {"login": LOGIN})
    years = data["user"]["contributionsCollection"].get("contributionYears", [])
    current = datetime.now(timezone.utc).year
    normalized = sorted({int(year) for year in years} | {current}, reverse=True)
    return normalized


def calendar_for_year(year: int) -> dict:
    now = datetime.now(timezone.utc)
    end = min(now.strftime("%Y-%m-%dT%H:%M:%SZ"), iso_year(year, end=True)) if year == now.year else iso_year(year, end=True)
    data = graphql(CALENDAR_QUERY, {"login": LOGIN, "from": iso_year(year), "to": end})
    return data["user"]["contributionsCollection"]["contributionCalendar"]


def month_label(month: dict, language: str) -> str:
    english = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
    spanish = {1: "ENE", 2: "FEB", 3: "MAR", 4: "ABR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AGO", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DIC"}
    try:
        number = int(str(month["firstDay"])[5:7])
    except (KeyError, ValueError):
        return str(month.get("name", ""))[:3].upper()
    return (spanish if language == "es" else english).get(number, "")


def render_calendar(calendar: dict, year: int, theme: dict, language: str) -> str:
    labels = LANG[language]
    weeks = calendar.get("weeks", [])
    total = int(calendar.get("totalContributions", 0))
    all_days = [day for week in weeks for day in week.get("contributionDays", [])]
    dates = [str(day["date"]) for day in all_days if day.get("date")]
    start_date = min(dates) if dates else f"{year}-01-01"
    end_date = max(dates) if dates else f"{year}-12-31"
    width, height = 1200, 360
    panel_x, panel_y, panel_w, panel_h, radius = 16, 16, 1168, 328, 34
    grid_x, grid_y, step, cell = 70, 142, 20, 13
    level_colors = theme["levels"]
    lines: list[str] = []
    lines.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">''')
    lines.append(f"  <title id=\"title\">{escape(labels['alt'].format(login=LOGIN, year=year))}</title>")
    lines.append(f"  <desc id=\"desc\">{escape(labels['desc'].format(login=LOGIN, total=total, start=start_date, end=end_date))}</desc>")
    lines.append("  <defs>")
    lines.append(f'''    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{theme['bg_start']}"/><stop offset="0.55" stop-color="{theme['bg_mid']}"/><stop offset="1" stop-color="{theme['bg_end']}"/></linearGradient>''')
    lines.append(f'''    <pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="{theme['grid']}" stroke-opacity=".055"/><circle cx="1" cy="1" r="1" fill="{theme['grid']}" opacity=".12"/></pattern>''')
    lines.append(f'''    <clipPath id="clip"><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}"/></clipPath>''')
    lines.append("  </defs>")
    lines.append(f'''  <g clip-path="url(#clip)"><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#bg)"/><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#grid)"/><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="none" stroke="{theme['panel_stroke']}" stroke-opacity=".22"/>''')
    lines.append("    <g font-family=\"monospace\">")
    lines.append(f'''      <text x="58" y="64" fill="{theme['ink']}" opacity=".82" font-size="14" font-weight="600" letter-spacing="3">{escape(labels['title'].format(year=year))}</text>''')
    lines.append(f'''      <text x="1142" y="64" text-anchor="end" fill="{theme['ink']}" font-size="22" font-weight="700">{total} <tspan font-size="12" opacity=".72">{labels['total']}</tspan></text>''')
    lines.append(f'''      <text x="58" y="92" fill="{theme['body']}" opacity=".9" font-size="14">{escape(labels['subtitle'])}</text>''')
    month_positions: dict[str, int] = {}
    for index, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            if day.get("date"):
                month_positions.setdefault(str(day["date"])[:7], index)
    for month in calendar.get("months", []):
        key = str(month.get("firstDay", ""))[:7]
        if key in month_positions:
            x = grid_x + month_positions[key] * step
            lines.append(f'''      <text x="{x}" y="116" fill="{theme['muted']}" opacity=".9" font-size="11" font-weight="600" letter-spacing="1">{month_label(month, language)}</text>''')
    for weekday, label in labels["weekdays"].items():
        lines.append(f'''      <text x="32" y="{grid_y + weekday * step + 10}" text-anchor="end" fill="{theme['muted']}" opacity=".84" font-size="10">{label}</text>''')
    for week_index, week in enumerate(weeks):
        x = grid_x + week_index * step
        for day in week.get("contributionDays", []):
            try:
                weekday = int(day.get("weekday", 0))
                count = int(day.get("contributionCount", 0))
            except (TypeError, ValueError):
                weekday, count = 0, 0
            level = day.get("contributionLevel", "NONE")
            fill = level_colors.get(level, theme["none"]) if count else theme["none"]
            date_value = escape(str(day.get("date", "")))
            word = labels["contribution"] if count == 1 else labels["contributions"]
            animate = ""
            if count:
                delay = ((week_index * 7 + weekday) % 13) * 0.18
                animate = f'<animate attributeName="opacity" values="0.72;1;0.72" dur="4.8s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
            lines.append(f'''      <rect x="{x}" y="{grid_y + weekday * step}" width="{cell}" height="{cell}" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1"><title>{date_value}: {count} {word}</title>{animate}</rect>''')
    legend_y = 306
    lines.append(f'''      <text x="58" y="316" fill="{theme['muted']}" opacity=".9" font-size="11">{labels['less']}</text>''')
    legend_colors = [theme["none"], level_colors["FIRST_QUARTILE"], level_colors["SECOND_QUARTILE"], level_colors["THIRD_QUARTILE"], level_colors["FOURTH_QUARTILE"]]
    for index, fill in enumerate(legend_colors):
        lines.append(f'''      <rect x="{98 + index * 22}" y="{legend_y}" width="14" height="14" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1"/>''')
    lines.append(f'''      <text x="218" y="316" fill="{theme['muted']}" opacity=".9" font-size="11">{labels['more']}</text>''')
    lines.append(f'''      <text x="1142" y="316" text-anchor="end" fill="{theme['muted']}" opacity=".8" font-size="11">{start_date} → {end_date}</text>''')
    lines.append("    </g></g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_history(calendars: dict[int, dict], years: list[int], theme: dict, language: str) -> str:
    labels = LANG[language]
    all_days = [day for year in years for week in calendars[year].get("weeks", []) for day in week.get("contributionDays", [])]
    total = sum(int(day.get("contributionCount", 0)) for day in all_days)
    dates = [str(day["date"]) for day in all_days if day.get("date")]
    start_date = min(dates) if dates else "unknown"
    end_date = max(dates) if dates else "unknown"
    width, row_height, top = 1200, 218, 134
    height = top + row_height * len(years) + 52
    panel_x, panel_y, panel_w, panel_h, radius = 16, 16, 1168, height - 32, 34
    grid_x, step, cell = 104, 20, 13
    level_colors = theme["levels"]
    lines: list[str] = []
    lines.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">''')
    lines.append(f"  <title id=\"title\">{escape(labels['alt'])}</title>")
    lines.append(f"  <desc id=\"desc\">{escape(labels['desc'].format(login=LOGIN, total=total, start=start_date, end=end_date))}</desc>")
    lines.append("  <defs>")
    lines.append(f'''    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{theme['bg_start']}"/><stop offset="0.55" stop-color="{theme['bg_mid']}"/><stop offset="1" stop-color="{theme['bg_end']}"/></linearGradient>''')
    lines.append(f'''    <pattern id="grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M38 0H0V38" fill="none" stroke="{theme['grid']}" stroke-opacity=".055"/><circle cx="1" cy="1" r="1" fill="{theme['grid']}" opacity=".12"/></pattern>''')
    lines.append(f'''    <clipPath id="clip"><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}"/></clipPath>''')
    lines.append("  </defs>")
    lines.append(f'''  <g clip-path="url(#clip)"><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#bg)"/><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="url(#grid)"/><rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="{radius}" fill="none" stroke="{theme['panel_stroke']}" stroke-opacity=".22"/>''')
    lines.append("    <g font-family=\"monospace\">")
    lines.append(f'''      <text x="58" y="64" fill="{theme['ink']}" opacity=".84" font-size="14" font-weight="600" letter-spacing="3">{escape(labels['history_title'])}</text>''')
    lines.append(f'''      <text x="1142" y="64" text-anchor="end" fill="{theme['ink']}" font-size="22" font-weight="700">{total} <tspan font-size="12" opacity=".72">{labels['total']}</tspan></text>''')
    lines.append(f'''      <text x="58" y="92" fill="{theme['body']}" opacity=".9" font-size="14">{escape(labels['history_subtitle'])}</text>''')
    for row_index, year in enumerate(years):
        row_y = top + row_index * row_height
        calendar = calendars[year]
        lines.append(f'''      <text x="58" y="{row_y + 30}" fill="{theme['ink']}" font-size="16" font-weight="700">{year}</text>''')
        lines.append(f'''      <text x="58" y="{row_y + 51}" fill="{theme['muted']}" font-size="11">{int(calendar.get('totalContributions', 0))} {labels['year_word']}</text>''')
        month_positions: dict[str, int] = {}
        for index, week in enumerate(calendar.get("weeks", [])):
            for day in week.get("contributionDays", []):
                if day.get("date"):
                    month_positions.setdefault(str(day["date"])[:7], index)
        for month in calendar.get("months", []):
            key = str(month.get("firstDay", ""))[:7]
            if key in month_positions:
                x = grid_x + month_positions[key] * step
                lines.append(f'''      <text x="{x}" y="{row_y + 15}" fill="{theme['muted']}" opacity=".88" font-size="10" font-weight="600">{month_label(month, language)}</text>''')
        for week_index, week in enumerate(calendar.get("weeks", [])):
            x = grid_x + week_index * step
            for day in week.get("contributionDays", []):
                try:
                    weekday = int(day.get("weekday", 0))
                    count = int(day.get("contributionCount", 0))
                except (TypeError, ValueError):
                    weekday, count = 0, 0
                level = day.get("contributionLevel", "NONE")
                fill = level_colors.get(level, theme["none"]) if count else theme["none"]
                date_value = escape(str(day.get("date", "")))
                word = labels["contribution"] if count == 1 else labels["contributions"]
                lines.append(f'''      <rect x="{x}" y="{row_y + 66 + weekday * step}" width="{cell}" height="{cell}" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1"><title>{date_value}: {count} {word}</title></rect>''')
    legend_y = top + row_height * len(years) + 10
    lines.append(f'''      <text x="58" y="{legend_y + 10}" fill="{theme['muted']}" opacity=".9" font-size="11">{labels['less']}</text>''')
    legend_colors = [theme["none"], level_colors["FIRST_QUARTILE"], level_colors["SECOND_QUARTILE"], level_colors["THIRD_QUARTILE"], level_colors["FOURTH_QUARTILE"]]
    for index, fill in enumerate(legend_colors):
        lines.append(f'''      <rect x="98" y="{legend_y}" width="14" height="14" rx="3" fill="{fill}" stroke="{theme['cell_stroke']}" stroke-width="1" transform="translate({index * 22} 0)"/>''')
    lines.append(f'''      <text x="218" y="{legend_y + 10}" fill="{theme['muted']}" opacity=".9" font-size="11">{labels['more']}</text>''')
    lines.append(f'''      <text x="1142" y="{legend_y + 10}" text-anchor="end" fill="{theme['muted']}" opacity=".8" font-size="11">{start_date} → {end_date}</text>''')
    lines.append("    </g></g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def build_translated_panels() -> None:
    for name in ("hero", "content", "evidence", "signal", "footer"):
        for suffix in ("", "-light"):
            source = ASSETS / f"{name}{suffix}.svg"
            target = ASSETS / f"{name}-es{suffix}.svg"
            text = source.read_text(encoding="utf-8")
            for old, new in PANEL_TRANSLATIONS.items():
                text = text.replace(old, new)
            target.write_text(text, encoding="utf-8")


def picture(asset_dark: str, asset_light: str, alt: str, width: str = "100%") -> str:
    return "\n".join([
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" srcset="./assets/{asset_dark}" />',
        f'  <source media="(prefers-color-scheme: light)" srcset="./assets/{asset_light}" />',
        f'  <img src="./assets/{asset_dark}" alt="{escape(alt)}" width="{width}" />',
        "</picture>",
    ])


def build_readme(years: list[int], calendars: dict[int, dict], language: str) -> str:
    spanish = language == "es"
    github_label = "&lt;/&gt; GITHUB · @xFrankB"
    contact_label = "[CORREO] CONTACTO · jfby13@gmail.com" if spanish else "[MAIL] CONTACT · jfby13@gmail.com"
    open_to = "DISPONIBLE PARA: oportunidades trainee / junior · construcciones colaborativas" if spanish else "OPEN TO: trainee / junior opportunities · collaborative builds"
    if spanish:
        hero = picture("hero-es.gif?v=17", "hero-es-light.gif?v=17", "xFrankB — Francisco Baylón", width="100%")
        content = picture("content-es.svg", "content-es-light.svg", "Perfil técnico, enfoque, proyecto, stack y contacto de xFrankB")
        evidence = picture("evidence-es.svg", "evidence-es-light.svg", "Evidencia pública del proyecto U3_APM y su estructura técnica")
        signal = picture("signal-es.svg", "signal-es-light.svg", "Señales técnicas verificables de xFrankB")
        footer = picture("footer-es.svg", "footer-es-light.svg", "Construir, aprender y repetir — xFrankB")
        contribution_alt = "Calendario de contribuciones públicas de xFrankB"
    else:
        hero = picture("hero.gif?v=17", "hero-light.gif?v=17", "xFrankB — Francisco Baylón", width="100%")
        content = picture("content.svg", "content-light.svg", "Technical profile, focus, project, stack and contact for xFrankB")
        evidence = picture("evidence.svg", "evidence-light.svg", "Public evidence of the U3_APM project and its technical structure")
        signal = picture("signal.svg", "signal-light.svg", "Verified technical signals for xFrankB")
        footer = picture("footer.svg", "footer-light.svg", "Build, learn, repeat — xFrankB")
        contribution_alt = "Current-year public contribution calendar for xFrankB"

    hero_layout = "\n".join([
        '<div align="center">',
        hero,
        '</div>',
    ])

    contribution = picture(
        "contributions-es.svg" if spanish else "contributions.svg",
        "contributions-es-light.svg" if spanish else "contributions-light.svg",
        contribution_alt,
    )
    return "\n".join([
        '<div align="center">', '', hero_layout, '',
        '<div align="center">',
        f'  <a href="https://github.com/xFrankB" title="GitHub"><kbd>{github_label}</kbd></a><br />',
        f'  <a href="mailto:jfby13@gmail.com" title="Contacto"><kbd>{contact_label}</kbd></a>',
        '</div>', '', '</div>', '',
        '<div align="center">', '', content, '', evidence, '', signal, '',
        contribution,
        '</div>', '',
        '<div align="center">', '', footer, '',
        f'<sub><code>{open_to}</code></sub>', '', '</div>', ''
    ])


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    candidate_years = available_years()
    technologies = detected_technologies()
    update_technology_orbit(technologies)
    print(f"technologies={', '.join(technologies)}")
    build_translated_panels()
    calendars: dict[int, dict] = {}
    for year in candidate_years:
        calendar = calendar_for_year(year)
        total = int(calendar.get("totalContributions", 0))
        if total > 0:
            calendars[year] = calendar
        print(f"year={year} total={total} weeks={len(calendar.get('weeks', []))}")
    years = sorted(calendars, reverse=True)
    if not years:
        years = [max(candidate_years)]
        calendars[years[0]] = {"totalContributions": 0, "months": [], "weeks": []}
    current_year = max(years)
    current_calendar = calendars[current_year]
    outputs = {
        ASSETS / "contributions.svg": render_calendar(current_calendar, current_year, DARK, "en"),
        ASSETS / "contributions-light.svg": render_calendar(current_calendar, current_year, LIGHT, "en"),
        ASSETS / "contributions-es.svg": render_calendar(current_calendar, current_year, DARK, "es"),
        ASSETS / "contributions-es-light.svg": render_calendar(current_calendar, current_year, LIGHT, "es"),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    calendar_dir = ROOT / "calendar"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    (calendar_dir / "data.json").write_text(
        json.dumps({"login": LOGIN, "currentYear": current_year, "years": years, "calendars": calendars}, ensure_ascii=False),
        encoding="utf-8",
    )
    expected = {path.name for path in outputs}
    for path in ASSETS.glob("contributions-*.svg"):
        if path.name not in expected:
            path.unlink()
    (ROOT / "README.md").write_text(build_readme(years, calendars, "en"), encoding="utf-8")
    (ROOT / "README.es.md").write_text(build_readme(years, calendars, "es"), encoding="utf-8")
    print(f"years={','.join(map(str, years))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise
