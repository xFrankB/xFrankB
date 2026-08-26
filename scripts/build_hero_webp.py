#!/usr/bin/env python3
"""Build smooth WebP heroes with continuous orbit motion and crisp static text."""
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
    moving_orbit_prefix,
    orbit_shell,
    static_logo,
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
ORBIT_PHASE_COUNT = 64
TECHNOLOGIES_RE = re.compile(r"<title>(.*?) — detected in public repositories</title>")
FADE_IN = ((0.06, 80), (0.12, 80), (0.20, 80), (0.30, 80), (0.44, 80), (0.62, 80), (0.82, 80))
FADE_OUT = ((0.82, 80), (0.62, 80), (0.44, 80), (0.30, 80), (0.20, 80), (0.12, 80), (0.06, 80))
HOLD_OPACITY = 1.0
HOLD_DURATION = 2080
HOLD_FRAME_DURATION = 520
SLOT_DURATION = sum(duration for _, duration in FADE_IN) + HOLD_DURATION + sum(duration for _, duration in FADE_OUT)


def technologies(source: str) -> list[str]:
    found = list(dict.fromkeys(TECHNOLOGIES_RE.findall(source)))
    if not found:
        raise RuntimeError("No technologies found in hero SVG")
    return found


def render(svg: str, width: int, height: int) -> Image.Image:
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=width, output_height=height)
    return Image.open(BytesIO(png)).convert("RGBA")


def static_base_svg(source: str) -> str:
    start = source.index(ORBIT_START)
    marker_end = source.index(ORBIT_END, start) + len(ORBIT_END)
    # Remove only the orbit block and its marker; retain the panel frame and
    # the outer group that follow the marker.
    return source[:start] + source[marker_end:]


def orbit_layer_svg(prefix: str, suffix: str, phase: float) -> str:
    moving = moving_orbit_prefix(prefix, phase)
    moving = moving.replace('transform="translate(820 28)"', 'transform="translate(0 0)"', 1)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ORBIT_WIDTH}" height="{ORBIT_HEIGHT}" '
        f'viewBox="0 0 {ORBIT_WIDTH} {ORBIT_HEIGHT}">{moving}{suffix}</svg>'
    )


def logo_layer_svg(technology: str, ordinal: int, total: int, opacity: float, light: bool) -> str:
    body = static_logo(technology, ordinal, total, opacity, light)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ORBIT_WIDTH}" height="{ORBIT_HEIGHT}" '
        f'viewBox="0 0 {ORBIT_WIDTH} {ORBIT_HEIGHT}">{body}</svg>'
    )


def phase_key(elapsed_ms: int, total_duration_ms: int) -> int:
    if total_duration_ms <= 0:
        return 0
    return int((elapsed_ms * ORBIT_PHASE_COUNT) / total_duration_ms) % ORBIT_PHASE_COUNT


def build(source_path: Path, output_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    techs = technologies(source)
    prefix, suffix = orbit_shell(source)
    light = "-light" in source_path.stem
    total_duration_ms = len(techs) * SLOT_DURATION

    # Render the crisp text/grid base once. Only the small orbit and logo layers
    # are recomposited per frame, so the fixed text never accumulates codec blur.
    base = render(static_base_svg(source), OUTPUT_WIDTH, OUTPUT_HEIGHT)
    orbit_frames = [
        render(orbit_layer_svg(prefix, suffix, key / ORBIT_PHASE_COUNT), ORBIT_WIDTH, ORBIT_HEIGHT)
        for key in range(ORBIT_PHASE_COUNT)
    ]
    logo_cache: dict[tuple[str, int], Image.Image] = {}
    opacities = tuple(opacity for opacity, _ in FADE_IN) + (HOLD_OPACITY,) + tuple(opacity for opacity, _ in FADE_OUT)
    for ordinal, technology in enumerate(techs, start=1):
        for state, opacity in enumerate(opacities):
            logo_cache[(technology, state)] = render(
                logo_layer_svg(technology, ordinal, len(techs), opacity, light),
                ORBIT_WIDTH,
                ORBIT_HEIGHT,
            )

    frames: list[Image.Image] = []
    durations: list[int] = []
    elapsed_ms = 0
    for ordinal, technology in enumerate(techs, start=1):
        for state, (opacity, duration) in enumerate(FADE_IN):
            frame = base.copy()
            frame.alpha_composite(orbit_frames[phase_key(elapsed_ms, total_duration_ms)], (ORBIT_X, ORBIT_Y))
            frame.alpha_composite(logo_cache[(technology, state)], (ORBIT_X, ORBIT_Y))
            frames.append(frame)
            durations.append(duration)
            elapsed_ms += duration

        # Keep the logo recognizable while advancing the orbit every 100 ms.
        hold_frames = HOLD_DURATION // HOLD_FRAME_DURATION
        for _ in range(hold_frames):
            frame = base.copy()
            frame.alpha_composite(orbit_frames[phase_key(elapsed_ms, total_duration_ms)], (ORBIT_X, ORBIT_Y))
            frame.alpha_composite(logo_cache[(technology, len(FADE_IN))], (ORBIT_X, ORBIT_Y))
            frames.append(frame)
            durations.append(HOLD_FRAME_DURATION)
            elapsed_ms += HOLD_FRAME_DURATION

        for offset, (opacity, duration) in enumerate(FADE_OUT, start=len(FADE_IN) + 1):
            frame = base.copy()
            frame.alpha_composite(orbit_frames[phase_key(elapsed_ms, total_duration_ms)], (ORBIT_X, ORBIT_Y))
            frame.alpha_composite(logo_cache[(technology, offset)], (ORBIT_X, ORBIT_Y))
            frames.append(frame)
            durations.append(duration)
            elapsed_ms += duration

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=False,
        quality=80,
        method=0,
    )
    print(f"{output_path.name}: {len(techs)} technologies, {len(frames)} frames, {output_path.stat().st_size} bytes")


def main() -> int:
    for source_name in HERO_FILES:
        build(ASSETS / source_name, ASSETS / WEBP_OUTPUTS[source_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
