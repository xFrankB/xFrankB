#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PANEL_NAMES = ("hero", "content", "evidence", "signal", "footer")

PALETTE = (
    ("#ffffff", "__WHITE_LONG__"),
    ("#fff", "__WHITE_SHORT__"),
    ("#0d1117", "__GITHUB_DARK__"),
    ("#050505", "#f3f3ef"),
    ("#060606", "#e7e7e2"),
    ("#030303", "#f8f8f5"),
    ("#0a0a0a", "#eeeeea"),
    ("#141414", "#fbfbf8"),
    ("#161616", "#fdfdfb"),
    ("#1d1d1d", "#deded9"),
    ("#777", "#858585"),
    ("#888", "#777777"),
    ("__WHITE_LONG__", "#151515"),
    ("__WHITE_SHORT__", "#151515"),
    ("__GITHUB_DARK__", "#ffffff"),
)

for name in PANEL_NAMES:
    for language_suffix in ("", "-es"):
        source = ASSETS / f"{name}{language_suffix}.svg"
        target = ASSETS / f"{name}{language_suffix}-light.svg"
        text = source.read_text(encoding="utf-8")
        for old, new in PALETTE:
            text = text.replace(old, new)
        # Guard against malformed concatenation from any cached/legacy short-hex transform.
        text = text.replace("#151515fff", "#ffffff")
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.name}")
