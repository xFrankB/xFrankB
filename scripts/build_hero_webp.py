#!/usr/bin/env python3
"""Build smooth, lightweight animated WebP heroes from optimized GIF frames."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
HERO_GIFS = ("hero.gif", "hero-light.gif", "hero-es.gif", "hero-es-light.gif")
INTERPOLATED_OUTPUTS = {name: name.replace(".gif", ".webp") for name in HERO_GIFS}
STATES_PER_TECHNOLOGY = 9
TRANSITION_STEPS = (1 / 3, 2 / 3)


def blend_frames(first: Image.Image, second: Image.Image, amount: float) -> Image.Image:
    return Image.blend(first, second, amount).convert("RGBA")


def build_webp(gif_path: Path, output_path: Path) -> None:
    source = Image.open(gif_path)
    source_frames: list[Image.Image] = []
    source_durations: list[int] = []
    for index in range(source.n_frames):
        source.seek(index)
        source_frames.append(source.convert("RGBA").copy())
        source_durations.append(int(source.info.get("duration", 100)))
    if len(source_frames) % STATES_PER_TECHNOLOGY:
        raise RuntimeError(f"Unexpected frame count in {gif_path.name}: {len(source_frames)}")

    technology_count = len(source_frames) // STATES_PER_TECHNOLOGY
    frames: list[Image.Image] = []
    durations: list[int] = []
    for technology_index in range(technology_count):
        start = technology_index * STATES_PER_TECHNOLOGY
        slot_frames = source_frames[start : start + STATES_PER_TECHNOLOGY]
        slot_durations = source_durations[start : start + STATES_PER_TECHNOLOGY]

        # Split each fade state into short blended frames. The stable logo
        # state keeps its original duration so it remains recognizable.
        for state in range(0, 4):
            step_duration = max(20, round(slot_durations[state] / (len(TRANSITION_STEPS) + 1)))
            frames.append(slot_frames[state])
            durations.append(step_duration)
            for amount in TRANSITION_STEPS:
                frames.append(blend_frames(slot_frames[state], slot_frames[state + 1], amount))
                durations.append(step_duration)

        frames.append(slot_frames[4])
        durations.append(slot_durations[4])

        for state in range(4, 8):
            step_duration = max(20, round(slot_durations[state] / (len(TRANSITION_STEPS) + 1)))
            frames.append(slot_frames[state])
            durations.append(step_duration)
            for amount in TRANSITION_STEPS:
                frames.append(blend_frames(slot_frames[state], slot_frames[state + 1], amount))
                durations.append(step_duration)

        frames.append(slot_frames[8])
        durations.append(slot_durations[8])

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=False,
        quality=70,
        method=0,
    )
    print(f"{output_path.name}: {technology_count} technologies, {len(frames)} frames, {output_path.stat().st_size} bytes")


def main() -> int:
    for gif_name in HERO_GIFS:
        build_webp(ASSETS / gif_name, ASSETS / INTERPOLATED_OUTPUTS[gif_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
