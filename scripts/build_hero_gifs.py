#!/usr/bin/env python3
"""Build animated, GitHub-compatible hero GIFs from the generated SVG panels."""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
from PIL import Image

from update_contributions import technology_mark

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
    suffix = "    </g>\n"
    return prefix, suffix


def static_card(technology: str, ordinal: int, total: int, opacity: float) -> str:
    label = escape(technology)
    mark = escape(technology_mark(technology))
    return "\n".join(
        [
            f'      <g opacity="{opacity:.2f}" aria-label="{label}">',
            f"        <title>{label} — active technology</title>",
            '        <rect x="22" y="70" width="296" height="174" rx="24" fill="#050505" fill-opacity="0.92" stroke="#ffffff" stroke-opacity="0.16" stroke-width="1.1"/>',
            '        <circle cx="170" cy="132" r="50" fill="#050505" fill-opacity="0.92" stroke="#ffffff" stroke-opacity="0.52" stroke-width="1.4"/>',
            f'        <text x="170" y="142" text-anchor="middle" fill="#ffffff" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="27" font-weight="700" letter-spacing="0.5">{mark}</text>',
            f'        <text x="170" y="204" text-anchor="middle" textLength="258" lengthAdjust="spacingAndGlyphs" fill="#ffffff" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="23" font-weight="700">{label}</text>',
            f'        <text x="170" y="226" text-anchor="middle" fill="#ffffff" fill-opacity="0.48" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="10" letter-spacing="1">{ordinal:02d} / {total:02d}</text>',
            "      </g>",
        ]
    )


def frame_svg(source: str, prefix: str, suffix: str, technology: str, ordinal: int, total: int, opacity: float) -> str:
    start = source.index(ORBIT_START)
    end = source.index(ORBIT_END, start) + len(ORBIT_END)
    replacement = prefix + static_card(technology, ordinal, total, opacity) + suffix + ORBIT_END
    return source[:start] + replacement + source[end:]


def rgba_to_gif_frame(png_bytes: bytes) -> Image.Image:
    rgba = Image.open(BytesIO(png_bytes)).convert("RGBA")
    alpha = rgba.getchannel("A")
    frame = rgba.convert("RGB").quantize(colors=63, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    transparent = frame.load()
    alpha_pixels = alpha.load()
    for y in range(frame.height):
        for x in range(frame.width):
            if alpha_pixels[x, y] < 18:
                transparent[x, y] = 0
    frame.info["transparency"] = 0
    return frame


def build_gif(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    technologies = extract_technologies(source)
    prefix, suffix = orbit_shell(source)
    frames: list[Image.Image] = []
    durations: list[int] = []
    # Each technology owns the full slot. The label fades in and out alone,
    # so no two technology names are ever composited in the same frame.
    sequence = ((0.24, 180), (0.62, 180), (1.0, 3000), (0.62, 180), (0.20, 180))
    for ordinal, technology in enumerate(technologies, start=1):
        for opacity, duration in sequence:
            svg = frame_svg(source, prefix, suffix, technology, ordinal, len(technologies), opacity)
            png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=OUTPUT_WIDTH, output_height=OUTPUT_HEIGHT)
            frames.append(rgba_to_gif_frame(png))
            durations.append(duration)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=True,
    )
    print(f"{output_path.name}: {len(technologies)} technologies, {len(frames)} frames, {output_path.stat().st_size} bytes")


def main() -> int:
    for source_name in HERO_FILES:
        build_gif(ASSETS / source_name, ASSETS / OUTPUT_FILES[source_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
