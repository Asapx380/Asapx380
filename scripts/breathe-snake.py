#!/usr/bin/env python3
"""Post-process Platane/snk SVGs: ease the crawl, pulse eaten cells, idle grid wave."""

from __future__ import annotations

import re
import sys
from pathlib import Path

BREATHE_MARK = "/* briaspas-breathe */"

CELL_KF = re.compile(
    r"@keyframes (c[0-9a-z]+)\s*\{\s*"
    r"([\d.]+)%\{fill:(var\(--c[1-4]\))\}\s*"
    r"[\d.]+%,100%\{fill:var\(--ce\)\}\s*"
    r"\}"
)

C_RULE = re.compile(
    r"\.c\{shape-rendering:geometricPrecision;fill:var\(--ce\);"
    r"stroke-width:1px;stroke:var\(--cb\);"
    r"animation:none (\d+)ms linear infinite;"
)

S_RULE = re.compile(
    r"\.s\{shape-rendering:geometricPrecision;fill:var\(--cs\);"
    r"animation:none linear (\d+)ms infinite\}"
)

U_RULE = re.compile(
    r"\.u\{transform-origin:0 0;transform:scale\(0,1\);"
    r"animation:none linear (\d+)ms infinite\}"
)

EMPTY_RECT = re.compile(
    r'<rect class="c" x="([^"]+)" y="([^"]+)"'
)

EASE = "cubic-bezier(.37,.02,.18,1)"
BREATHE_PERIOD = 5.4


def expand_cell(match: re.Match[str]) -> str:
    name, peak_s, color = match.group(1), match.group(2), match.group(3)
    peak = float(peak_s)
    fade_in = max(0.0, peak - 4.2)
    hold = min(96.0, peak + 5.5)
    fade_out = min(100.0, hold + 7.0)
    return (
        f"@keyframes {name}{{"
        f"0%,{fade_in:.2f}%{{fill:var(--ce);opacity:1}}"
        f"{peak:.2f}%{{fill:{color};opacity:1}}"
        f"{hold:.2f}%{{fill:{color};opacity:1}}"
        f"{fade_out:.2f}%,100%{{fill:var(--ce);opacity:1}}"
        f"}}"
    )


def extra_css() -> str:
    period = BREATHE_PERIOD
    return (
        BREATHE_MARK
        + "@keyframes breathe{"
        + "0%,100%{opacity:.34}"
        + "50%{opacity:1}"
        + "}"
        + "@keyframes glow{"
        + "0%,100%{filter:drop-shadow(0 0 1.2px var(--cs))}"
        + "50%{filter:drop-shadow(0 0 5px var(--cs))}"
        + "}"
        + ".idle{animation:breathe "
        + str(period)
        + "s ease-in-out infinite}"
        + ".s{filter:drop-shadow(0 0 2.4px var(--cs))}"
        + "@media (prefers-reduced-motion:reduce){"
        + ".c,.s,.u,.idle{animation:none!important;filter:none!important;opacity:1}"
        + "}"
    )


def patch_empty(match: re.Match[str]) -> str:
    x, y = float(match.group(1)), float(match.group(2))
    col = max(0.0, (x - 2.0) / 16.0)
    row = max(0.0, (y - 2.0) / 16.0)
    delay = (col * 0.092 + row * 0.22) % BREATHE_PERIOD
    return (
        f'<rect class="c idle" x="{match.group(1)}" y="{match.group(2)}" '
        f'style="animation-delay:-{delay:.2f}s"'
    )


def transform(svg: str) -> str:
    if BREATHE_MARK in svg:
        return svg
    style_start = svg.find("<style>")
    style_end = svg.find("</style>")
    if style_start < 0 or style_end < 0:
        raise SystemExit("SVG sem bloco <style>")
    style = svg[style_start + 7 : style_end]
    new_style, n_kf = CELL_KF.subn(expand_cell, style)
    new_style, n_c = C_RULE.subn(
        rf".c{{shape-rendering:geometricPrecision;fill:var(--ce);"
        rf"stroke-width:1px;stroke:var(--cb);"
        rf"animation:none \1ms {EASE} infinite;",
        new_style,
        count=1,
    )
    new_style, n_s = S_RULE.subn(
        rf".s{{shape-rendering:geometricPrecision;fill:var(--cs);"
        rf"animation:none {EASE} \1ms infinite,glow 2.2s ease-in-out infinite}}",
        new_style,
        count=1,
    )
    # Keep snake path name + glow. snk sets animation-name on .s.s0 etc.
    new_style = re.sub(
        r"(\.s\.s[0-3]\{transform:[^;]+;animation-name:)(s[0-3])\}",
        r"\1\2,glow}",
        new_style,
    )
    new_style, n_u = U_RULE.subn(
        rf".u{{transform-origin:0 0;transform:scale(0,1);"
        rf"animation:none {EASE} \1ms infinite}}",
        new_style,
        count=1,
    )
    new_style += extra_css()
    body = svg[: style_start + 7] + new_style + svg[style_end:]
    body, n_idle = EMPTY_RECT.subn(patch_empty, body)
    if n_kf < 1 or n_c != 1 or n_s != 1:
        raise SystemExit(
            f"patch incompleto: kf={n_kf} c={n_c} s={n_s} u={n_u} idle={n_idle}"
        )
    return body


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit("uso: breathe-snake.py arquivo.svg [...]")
    for raw in argv[1:]:
        path = Path(raw)
        original = path.read_text(encoding="utf-8")
        path.write_text(transform(original), encoding="utf-8")
        print(f"ok {path}")


if __name__ == "__main__":
    main(sys.argv)
