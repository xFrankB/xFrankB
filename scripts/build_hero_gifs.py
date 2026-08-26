#!/usr/bin/env python3
"""Build animated, GitHub-compatible hero GIFs from generated SVG panels."""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT_WIDTH = 900
OUTPUT_HEIGHT = 285
HERO_FILES = ("hero.svg", "hero-light.svg", "hero-es.svg", "hero-es-light.svg")
OUTPUT_FILES = {
    "hero.svg": "hero.gif",
    "hero-light.svg": "hero-light.gif",
    "hero-es.svg": "hero-es.gif",
    "hero-es-light.svg": "hero-es-light.gif",
}
ORBIT_START = "    <!-- TECH_ORBIT_START -->"
ORBIT_END = "    <!-- TECH_ORBIT_END -->"
TECH_GROUP_START = '      <g opacity="0">'
ICON_FILES = {
    "TypeScript": "typescript.svg",
    "JavaScript": "javascript.svg",
    "Python": "python.svg",
    "React": "react.svg",
    "Vite": "vite.svg",
    "Node.js": "nodedotjs.svg",
    "Express": "express.svg",
    "pnpm": "pnpm.svg",
    "HTML": "html5.svg",
    "CSS": "css.svg",
    "Tailwind CSS": "tailwindcss.svg",
    "Git": "git.svg",
    "GitHub Actions": "githubactions.svg",
    "Linux": "linux.svg",
    "Axios": "axios.svg",
    "Framer Motion": "framer.svg",
    "Zod": "zod.svg",
}


def extract_technologies(source: str) -> list[str]:
    technologies = re.findall(r"<title>(.*?) — detected in public repositories</title>", source)
    unique = list(dict.fromkeys(technologies))
    if not unique:
        raise RuntimeError("No detected technologies found in the generated hero")
    return unique


def orbit_shell(source: str) -> tuple[str, str]:
    start = source.index(ORBIT_START)
    end = source.index(ORBIT_END, start)
    orbit = source[start:end]
    tech_start = orbit.index(TECH_GROUP_START)
    prefix = orbit[:tech_start]
    prefix = re.sub(r'\s*<text[^>]*>/ ACTIVE_STACK</text>\s*', "\n", prefix)
    suffix = "    </g>\n"
    return prefix, suffix


def icon_paths(technology: str) -> list[str]:
    filename = ICON_FILES.get(technology)
    if filename:
        icon = ASSETS / "tech-icons" / filename
        if icon.exists():
            paths = re.findall(r'<path\b[^>]*\bd="([^"]+)"', icon.read_text(encoding="utf-8"))
            if paths:
                return paths
    # A neutral fallback keeps newly detected technologies visible without
    # reintroducing a text label when no local brand mark is available yet.
    return ["M12 2.5a9.5 9.5 0 1 0 0 19 9.5 9.5 0 0 0 0-19Zm0 3a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Zm-1.5 3h3v3h-3v-3Zm0 4.5h3v3h-3v-3Z"]


def static_logo(technology: str, ordinal: int, total: int, opacity: float, light: bool) -> str:
    label = escape(technology)
    logo_color = "#151515" if light else "#d3d3d3"
    halo_color = "#151515" if light else "#ffffff"
    paths = "\n".join(
        f'          <path d="{path}" fill="{logo_color}" fill-opacity="0.68"/>'
        for path in icon_paths(technology)
    )
    return "\n".join(
        [
            f'      <g opacity="{opacity:.2f}" aria-label="{label}">',
            f"        <title>{label} — active technology logo</title>",
            f'        <circle cx="170" cy="132" r="57" fill="{halo_color}" fill-opacity="0.018" stroke="{halo_color}" stroke-opacity="0.17" stroke-width="1"/>',
            f'        <circle cx="170" cy="132" r="48" fill="none" stroke="{halo_color}" stroke-opacity="0.24" stroke-width="1.1"/>',
            '        <svg x="138" y="100" width="64" height="64" viewBox="0 0 24 24" aria-hidden="true">',
            paths,
            "        </svg>",
            f'        <text x="170" y="184" text-anchor="middle" textLength="138" lengthAdjust="spacingAndGlyphs" fill="{logo_color}" fill-opacity="0.62" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="11" letter-spacing="0.2">{label}</text>',
            "      </g>",
        ]
    )


def frame_svg(source: str, prefix: str, suffix: str, technology: str, ordinal: int, total: int, opacity: float, light: bool) -> str:
    start = source.index(ORBIT_START)
    end = source.index(ORBIT_END, start) + len(ORBIT_END)
    replacement = prefix + static_logo(technology, ordinal, total, opacity, light) + suffix + ORBIT_END
    return source[:start] + replacement + source[end:]


def rgba_to_gif_frame(png_bytes: bytes) -> Image.Image:
    rgba = Image.open(BytesIO(png_bytes)).convert("RGBA")
    alpha = rgba.getchannel("A")
    frame = rgba.convert("RGB").quantize(colors=63, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    transparent_index = 255
    palette = frame.getpalette()
    palette[transparent_index * 3 : transparent_index * 3 + 3] = [0, 0, 0]
    frame.putpalette(palette)
    pixels = frame.load()
    alpha_pixels = alpha.load()
    for y in range(frame.height):
        for x in range(frame.width):
            if alpha_pixels[x, y] < 18:
                pixels[x, y] = transparent_index
    frame.info["transparency"] = transparent_index
    return frame


def build_gif(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    technologies = extract_technologies(source)
    prefix, suffix = orbit_shell(source)
    frames: list[Image.Image] = []
    durations: list[int] = []
    light = "-light" in source_path.stem
    # Nine intermediate opacity states make the transition continuous while
    # only one logo is ever present in a frame. The active state stays long
    # enough to be recognizable in a short mobile screen recording.
    sequence = ((0.06, 160), (0.16, 160), (0.30, 160), (0.52, 140), (1.0, 2600), (0.52, 140), (0.30, 160), (0.16, 160), (0.06, 160))
    for ordinal, technology in enumerate(technologies, start=1):
        for opacity, duration in sequence:
            svg = frame_svg(source, prefix, suffix, technology, ordinal, len(technologies), opacity, light)
            png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=OUTPUT_WIDTH, output_height=OUTPUT_HEIGHT)
            frames.append(rgba_to_gif_frame(png))
            durations.append(duration)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=1,
        optimize=True,
        transparency=frames[0].info.get("transparency", 0),
    )
    print(f"{output_path.name}: {len(technologies)} technologies, {len(frames)} frames, {output_path.stat().st_size} bytes")


def main() -> int:
    for source_name in HERO_FILES:
        build_gif(ASSETS / source_name, ASSETS / OUTPUT_FILES[source_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
