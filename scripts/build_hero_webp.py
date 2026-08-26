#!/usr/bin/env python3
"""Build high-quality animated WebP heroes with static base and dynamic layers."""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

from build_hero_gifs import (
    ASSETS,
    HERO_FILES,
    ORBIT_END,
    ORBIT_START,
    static_logo,
    moving_orbit_prefix,
    orbit_shell,
)

WEBP_OUTPUTS = {
    "hero.svg": "hero.webp",
    "hero-light.svg": "hero-light.webp",
    "hero-es.svg": "hero-es.webp",
    "hero-es-light.svg": "hero-es-light.webp",
}
OUTPUT_WIDTH = 1200
OUTPUT_HEIGHT = 380
ORBIT_X = 820
ORBIT_Y = 28
ORBIT_WIDTH = 340
ORBIT_HEIGHT = 280
TECHNOLOGIES_RE = re.compile(r"<title>(.*?) — detected in public repositories</title>")
# 15 steps per technology for smooth transitions.
SEQUENCE = (
    (0.06, 80), (0.12, 80), (0.20, 80), (0.30, 80), (0.44, 80),
    (0.62, 80), (0.82, 80), (1.0, 2600),
    (0.82, 80), (0.62, 80), (0.44, 80), (0.30, 80), (0.20, 80),
    (0.12, 80), (0.06, 80),
)


def technologies(source: str) -> list[str]:
    found = list(dict.fromkeys(TECHNOLOGIES_RE.findall(source)))
    if not found:
        raise RuntimeError("No technologies found in hero SVG")
    return found


def render(svg: str, width: int, height: int) -> Image.Image:
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=width, output_height=height)
    return Image.open(BytesIO(png)).convert("RGBA")


def base_svg(source: str, prefix: str, suffix: str, phase: float) -> str:
    start = source.index(ORBIT_START)
    end = source.index(ORBIT_END, start) + len(ORBIT_END)
    moving = moving_orbit_prefix(prefix, phase)
    return source[:start] + moving + suffix + ORBIT_END + source[end:]


def overlay_svg(technology: str, ordinal: int, total: int, opacity: float, light: bool) -> str:
    body = static_logo(technology, ordinal, total, opacity, light)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ORBIT_WIDTH}" height="{ORBIT_HEIGHT}" '
        f'viewBox="0 0 {ORBIT_WIDTH} {ORBIT_HEIGHT}">{body}</svg>'
    )


def build(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    techs = technologies(source)
    prefix, suffix = orbit_shell(source)
    light = "-light" in source_path.stem

    # Render each orbital phase once at the original 1200x380 hero resolution.
    # The galaxy has 30 distinct phases in the loop.
    base_frames: dict[int, Image.Image] = {}
    phase_count = len(SEQUENCE) * 2
    for key in range(phase_count):
        base_frames[key] = render(
            base_svg(source, prefix, suffix, key / phase_count),
            OUTPUT_WIDTH,
            OUTPUT_HEIGHT,
        )

    overlay_cache: dict[tuple[str, int], Image.Image] = {}
    for tech in techs:
        for index, (opacity, _) in enumerate(SEQUENCE):
            overlay_cache[(tech, index)] = render(
                overlay_svg(tech, techs.index(tech) + 1, len(techs), opacity, light),
                ORBIT_WIDTH,
                ORBIT_HEIGHT,
            )

    frames: list[Image.Image] = []
    durations: list[int] = []
    for ordinal, tech in enumerate(techs, start=1):
        for phase_index, (_, duration) in enumerate(SEQUENCE):
            phase_key = ((ordinal - 1) * len(SEQUENCE) + phase_index) % phase_count
            frame = base_frames[phase_key].copy()
            frame.alpha_composite(overlay_cache[(tech, phase_index)], (ORBIT_X, ORBIT_Y))
            frames.append(frame)
            durations.append(duration)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=False,
        quality=88,
        method=0,
    )
    print(f"{output_path.name}: {len(techs)} technologies, {len(frames)} frames, {output_path.stat().st_size} bytes")


def main() -> int:
    for source_name in HERO_FILES:
        build(ASSETS / source_name, ASSETS / WEBP_OUTPUTS[source_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
