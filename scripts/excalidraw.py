"""Turn a small JSON diagram spec into an Excalidraw scene (.excalidraw) and a hand-drawn SVG (.svg).

Adapted from bits-studio's excalidraw.py + lint.py, plus a pure-Python deterministic
hand-drawn SVG renderer so GitHub Actions builds never depend on external servers.
"""

from __future__ import annotations

import html
import json
import math
from typing import Any

PALETTE = {
    "yellow": "#f9f3e4",
    "blue": "#e8f0f4",
    "green": "#e6f2eb",
    "red": "#faeae4",
    "violet": "#efecf4",
    "gray": "#f3f6f4",
    "orange": "#faeae4",
    "amber": "#f9f3e4",
    "none": "transparent",
}

STROKE_PALETTE = {
    "#f9f3e4": "#9a6c2a",
    "#e8f0f4": "#335c73",
    "#e6f2eb": "#1f6a44",
    "#faeae4": "#a93b1f",
    "#efecf4": "#5c4d6b",
    "#f3f6f4": "#8d9c94",
}

INK = "#141d18"
MUTED = "#4b5b53"
ACCENT = "#a93b1f"

BOX_W = 240
BOX_H = 118
GAP_X = 110
GAP_Y = 165
PER_ROW = 3
HAND_FONT = 1
LAYOUTS = {"flow", "stack", "grid", "tree"}
MAX_NODES = 8
TOL = 3.0


def _base(kind: str, x: float, y: float, w: float, h: float, seed: int) -> dict[str, Any]:
    return {
        "id": f"{kind}-{seed}",
        "type": kind,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(w, 2),
        "height": round(h, 2),
        "angle": 0,
        "strokeColor": INK,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": 1000 + seed * 37,
        "version": 1,
        "versionNonce": 1000 + seed * 91,
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def _text(
    content: str,
    x: float,
    y: float,
    seed: int,
    size: int = 20,
    color: str = INK,
    align: str = "left",
    width: float | None = None,
) -> dict[str, Any]:
    char_w = size * 0.58
    w = width if width is not None else max(len(content) * char_w, size)
    el = _base("text", x, y, w, size * 1.25, seed)
    el.update(
        {
            "strokeColor": color,
            "roundness": None,
            "text": content,
            "originalText": content,
            "fontSize": size,
            "fontFamily": HAND_FONT,
            "textAlign": align,
            "verticalAlign": "top",
            "containerId": None,
            "lineHeight": 1.25,
            "autoResize": align == "left",
        }
    )
    return el


def _centered(
    content: str, box_x: float, y: float, seed: int, size: int, color: str = INK
) -> dict[str, Any]:
    width = len(content) * size * 0.58
    return _text(content, box_x + (BOX_W - width) / 2, y, seed, size=size, color=color)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= width or not cur:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _box(node: dict[str, Any], x: float, y: float, seed: int) -> list[dict[str, Any]]:
    color = PALETTE.get(str(node.get("color", "yellow")), PALETTE["yellow"])
    shape = "ellipse" if node.get("shape") == "ellipse" else "rectangle"
    rect = _base(shape, x, y, BOX_W, BOX_H, seed)
    rect["backgroundColor"] = color
    rect["fillStyle"] = "solid"
    out = [rect]

    label_lines = _wrap(str(node.get("label", "")), 17)[:2]
    note_lines = _wrap(str(node.get("note", "") or ""), 27)[:2]

    label_h = len(label_lines) * 26
    note_h = (8 + len(note_lines) * 19) if note_lines else 0
    top = y + (BOX_H - label_h - note_h) / 2

    for i, line in enumerate(label_lines):
        out.append(_centered(line, x, top + i * 26, seed * 10 + i, 20))
    for j, line in enumerate(note_lines):
        out.append(
            _centered(line, x, top + label_h + 8 + j * 19, seed * 10 + 5 + j, 14, MUTED)
        )
    return out


def _arrow(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    seed: int,
    label: str = "",
    dashed: bool = False,
    via: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    pts = [(0.0, 0.0)]
    for vx, vy in via or []:
        pts.append((vx - x1, vy - y1))
    pts.append((x2 - x1, y2 - y1))

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    el = _base("arrow", x1, y1, max(xs) - min(xs), max(ys) - min(ys), seed)
    el.update(
        {
            "points": [[round(px, 2), round(py, 2)] for px, py in pts],
            "lastCommittedPoint": None,
            "startBinding": None,
            "endBinding": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "roundness": {"type": 2},
            "strokeStyle": "dashed" if dashed else "solid",
            "strokeColor": MUTED if dashed else INK,
        }
    )
    out = [el]
    if label:
        (ax, ay), (bx, by) = max(
            zip(pts, pts[1:]), key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1])
        )
        mx = x1 + (ax + bx) / 2
        my = y1 + (ay + by) / 2
        width = len(label) * 13 * 0.58
        if abs(bx - ax) >= abs(by - ay):
            tx, ty = mx - width / 2, my - 26
        else:
            tx, ty = mx + 14, my - 8
        out.append(_text(label, tx, ty, seed * 3 + 1, size=13, color=MUTED))
    return out


def _per_row(count: int) -> int:
    if count <= 3:
        return max(count, 1)
    if count == 4:
        return 2
    return PER_ROW


def _route(
    a: tuple[float, float],
    b: tuple[float, float],
    seed: int,
    label: str,
    dashed: bool,
    bottom: float,
) -> list[dict[str, Any]]:
    same_row = abs(a[1] - b[1]) < 1
    same_col = abs(a[0] - b[0]) < 1
    step = BOX_W + GAP_X

    if same_row and abs(b[0] - a[0]) <= step + 1:
        if b[0] > a[0]:
            return _arrow(a[0] + BOX_W + 8, a[1] + BOX_H / 2, b[0] - 8, b[1] + BOX_H / 2, seed, label, dashed)
        return _arrow(a[0] - 8, a[1] + BOX_H / 2, b[0] + BOX_W + 8, b[1] + BOX_H / 2, seed, label, dashed)

    if same_col and abs(b[1] - a[1]) <= GAP_Y + 1:
        if b[1] > a[1]:
            return _arrow(
                a[0] + BOX_W / 2, a[1] + BOX_H + 8, b[0] + BOX_W / 2, b[1] - 8,
                seed, label, dashed,
            )
        return _arrow(
            a[0] + BOX_W / 2, a[1] - 8, b[0] + BOX_W / 2, b[1] + BOX_H + 8,
            seed, label, dashed,
        )

    lane = bottom + 70
    return _arrow(
        a[0] + BOX_W / 2,
        a[1] + BOX_H + 8,
        b[0] + BOX_W / 2,
        b[1] + BOX_H + 8,
        seed,
        label,
        dashed,
        via=[(a[0] + BOX_W / 2, lane), (b[0] + BOX_W / 2, lane)],
    )


def _scene(elements: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "bits-studio",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }


def build_scene(spec: dict[str, Any]) -> dict[str, Any]:
    layout = str(spec.get("layout", "flow"))
    elements: list[dict[str, Any]] = []
    seed = 1

    title = str(spec.get("title", "") or "")
    y0 = 0.0
    if title:
        elements.append(_text(title, 0, 0, seed, size=24))
        seed += 1
        y0 = 60.0

    if layout == "grid":
        elements += _layout_grid(spec, y0, seed)
        return _scene(elements)
    if layout == "tree":
        elements += _layout_tree(spec, y0, seed)
        return _scene(elements)

    nodes = list(spec.get("nodes", []))
    positions: dict[str, tuple[float, float]] = {}
    per_row = 1 if layout == "stack" else _per_row(len(nodes))

    for i, node in enumerate(nodes):
        row = i // per_row
        col = i % per_row
        if row % 2 == 1 and per_row > 1:
            col = per_row - 1 - col
        x = col * (BOX_W + GAP_X)
        y = y0 + row * GAP_Y
        positions[str(node.get("id", i))] = (x, y)
        elements += _box(node, x, y, seed)
        seed += 1

    bottom = max((p[1] for p in positions.values()), default=y0) + BOX_H
    for edge in spec.get("edges", []):
        a = positions.get(str(edge.get("from")))
        b = positions.get(str(edge.get("to")))
        if not a or not b:
            continue
        label = str(edge.get("label", "") or "")
        dashed = bool(edge.get("dashed"))
        elements += _route(a, b, seed, label, dashed, bottom)
        seed += 1

    right_edge = max((p[0] for p in positions.values()), default=0.0) + BOX_W
    for callout in spec.get("callouts", []):
        pos = positions.get(str(callout.get("at")))
        text = str(callout.get("text", "") or "")
        if not pos or not text:
            continue
        lines = _wrap(text, 24)[:3]
        cx = right_edge + 90
        cy = pos[1] + BOX_H / 2 - len(lines) * 11
        for k, line in enumerate(lines):
            elements.append(_text(line, cx, cy + k * 22, seed * 7 + k, size=15, color=ACCENT))
        elements += _arrow(
            cx - 16, cy + len(lines) * 11, pos[0] + BOX_W + 10, pos[1] + BOX_H / 2,
            seed + 500, dashed=True,
        )
        seed += 1

    return _scene(elements)


def _layout_grid(spec: dict[str, Any], y0: float, seed: int) -> list[dict[str, Any]]:
    cells = spec.get("cells") or []
    gap = 10
    size = 16
    char_w = size * 0.58
    elements: list[dict[str, Any]] = []
    if not cells:
        return elements

    cols = max(len(row) for row in cells)
    grid: list[list[tuple[str, bool, list[str]]]] = []
    for row in cells:
        parsed: list[tuple[str, bool, list[str]]] = []
        for c in range(cols):
            raw = "" if c >= len(row) or row[c] is None else str(row[c])
            hit = raw.startswith("*")
            value = raw[1:] if hit else raw
            parsed.append((value, hit, _wrap(value, 14)))
        grid.append(parsed)

    col_w = [
        max(
            [74.0]
            + [max(len(ln) for ln in grid[r][c][2]) * char_w + 28 for r in range(len(grid))]
        )
        for c in range(cols)
    ]
    row_h = [max(56.0, max(len(cell[2]) for cell in row) * 22 + 26) for row in grid]
    xs = [sum(col_w[:c]) + c * gap for c in range(cols)]
    ys = [y0 + sum(row_h[:r]) + r * gap for r in range(len(grid))]

    for r, row in enumerate(grid):
        for c, (value, hit, lines) in enumerate(row):
            sq = _base("rectangle", xs[c], ys[r], col_w[c], row_h[r], seed)
            sq["backgroundColor"] = PALETTE["orange"] if hit else (PALETTE["blue"] if r == 0 else PALETTE["gray"])
            sq["fillStyle"] = "solid"
            elements.append(sq)
            seed += 1
            if not value:
                continue
            top = ys[r] + (row_h[r] - len(lines) * 22) / 2
            for i, line in enumerate(lines):
                width = len(line) * char_w
                elements.append(
                    _text(
                        line,
                        xs[c] + (col_w[c] - width) / 2,
                        top + i * 22,
                        seed,
                        size=size,
                    )
                )
                seed += 1

    return elements


def _layout_tree(spec: dict[str, Any], y0: float, seed: int) -> list[dict[str, Any]]:
    levels = spec.get("levels") or []
    size = 17
    char_w = size * 0.58
    wrapped = [[_wrap(str(label), 16)[:2] for label in level] for level in levels]
    longest = max(
        (len(ln) for level in wrapped for lines in level for ln in lines), default=8
    )
    w = max(170.0, longest * char_w + 32)
    h = 78.0 if all(len(lines) == 1 for level in wrapped for lines in level) else 96.0
    gap_x, gap_y = 40.0, h + 46
    widest = max((len(lv) for lv in levels), default=1)
    total = widest * (w + gap_x)
    coords: list[list[tuple[float, float]]] = []
    elements: list[dict[str, Any]] = []
    for li, level in enumerate(wrapped):
        row: list[tuple[float, float]] = []
        span = total / max(len(level), 1)
        for ni, lines in enumerate(level):
            x = ni * span + (span - w) / 2
            y = y0 + li * gap_y
            row.append((x, y))
            rect = _base("rectangle", x, y, w, h, seed)
            rect["backgroundColor"] = PALETTE["violet"] if li == 0 else PALETTE["blue"]
            rect["fillStyle"] = "solid"
            elements.append(rect)
            seed += 1
            top = y + (h - len(lines) * 23) / 2
            for i, line in enumerate(lines):
                elements.append(
                    _text(
                        line,
                        x + (w - len(line) * char_w) / 2,
                        top + i * 23,
                        seed,
                        size=size,
                    )
                )
                seed += 1
        coords.append(row)

    for li in range(len(coords) - 1):
        parents = coords[li]
        children = coords[li + 1]
        if not parents or not children:
            continue
        for ci, (cx, cy) in enumerate(children):
            px, py = parents[ci * len(parents) // len(children)]
            elements += _arrow(px + w / 2, py + h + 6, cx + w / 2, cy - 6, seed)
            seed += 1
    return elements


def lint(spec: Any, scene: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    problems: list[str] = []
    layout = str(spec.get("layout", "flow"))
    if layout not in LAYOUTS:
        problems.append(f"unknown layout {layout!r}; use one of {sorted(LAYOUTS)}")
    if not spec.get("caption"):
        problems.append("missing caption: say what the reader should notice")

    if layout == "grid":
        cells = spec.get("cells") or []
        if not cells:
            problems.append("grid has no cells")
        for r, row in enumerate(cells):
            for c, cell in enumerate(row):
                if cell is not None and len(str(cell)) > 28:
                    problems.append(f"grid cell ({r},{c}) is a sentence; keep cells to a number or two words")
        return problems

    if layout == "tree":
        levels = spec.get("levels") or []
        if len(levels) < 2:
            problems.append("tree needs at least two levels")
        return problems

    nodes = spec.get("nodes") or []
    if not nodes:
        return problems + ["no nodes"]
    if len(nodes) > MAX_NODES:
        problems.append(f"{len(nodes)} nodes; split the figure, max is {MAX_NODES}")
    ids = [str(n.get("id", i)) for i, n in enumerate(nodes)]
    if len(set(ids)) != len(ids):
        problems.append("duplicate node ids")
    for n in nodes:
        label = str(n.get("label", ""))
        note = str(n.get("note", "") or "")
        if len(_wrap(label, 17)) > 2:
            problems.append(f"label {label!r} is too long; max 4 words")
        if len(_wrap(note, 27)) > 2:
            problems.append(f"note {note!r} is too long; max 6 words")
    return problems


def _jitter(val: float, seed: int, amp: float = 1.6) -> float:
    return val + math.sin(seed * 12.9898) * amp


def scene_to_svg(scene: dict[str, Any]) -> str:
    """Render an Excalidraw scene dictionary into a crisp editorial architectural SVG."""
    els = [e for e in scene.get("elements", []) if not e.get("isDeleted")]
    if not els:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"></svg>'

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    for e in els:
        ex, ey = float(e.get("x", 0)), float(e.get("y", 0))
        ew, eh = float(e.get("width", 0)), float(e.get("height", 0))
        if e["type"] == "arrow":
            for px, py in e.get("points", []):
                min_x = min(min_x, ex + px)
                min_y = min(min_y, ey + py)
                max_x = max(max_x, ex + px)
                max_y = max(max_y, ey + py)
        else:
            min_x = min(min_x, ex)
            min_y = min(min_y, ey)
            max_x = max(max_x, ex + ew)
            max_y = max(max_y, ey + eh)

    pad = 34.0
    vx = min_x - pad
    vy = min_y - pad
    vw = max(240.0, (max_x - min_x) + pad * 2)
    vh = max(120.0, (max_y - min_y) + pad * 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.1f} {vy:.1f} {vw:.1f} {vh:.1f}" width="100%" height="auto" class="excalidraw-svg">',
        "<defs>",
        '<pattern id="draft-dots" width="22" height="22" patternUnits="userSpaceOnUse">',
        '<circle cx="11" cy="11" r="1.15" fill="#c7d3cc" opacity="0.65" />',
        "</pattern>",
        '<filter id="card-shadow" x="-10%" y="-10%" width="125%" height="130%">',
        '<feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#141d18" flood-opacity="0.08" />',
        "</filter>",
        "<style>",
        '.ed-title { font-family: "Bricolage Grotesque", -apple-system, BlinkMacSystemFont, sans-serif; letter-spacing: -0.015em; }',
        '.ed-label { font-family: "Bricolage Grotesque", -apple-system, BlinkMacSystemFont, sans-serif; }',
        '.ed-mono  { font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace; }',
        "</style>",
        "</defs>",
        # Subtle architectural blueprint paper background
        f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{vw:.1f}" height="{vh:.1f}" rx="14" fill="#fbfcfb" />',
        f'<rect x="{vx:.1f}" y="{vy:.1f}" width="{vw:.1f}" height="{vh:.1f}" rx="14" fill="url(#draft-dots)" />',
    ]

    for e in els:
        kind = e["type"]
        x = float(e.get("x", 0))
        y = float(e.get("y", 0))
        w = float(e.get("width", 0))
        h = float(e.get("height", 0))
        stroke = e.get("strokeColor", INK)
        bg = e.get("backgroundColor", "transparent")
        sw = float(e.get("strokeWidth", 1.8))
        is_dashed = e.get("strokeStyle") == "dashed"
        dash = ' stroke-dasharray="6 5"' if is_dashed else ""

        if kind == "rectangle":
            accent_bar = STROKE_PALETTE.get(bg, "#4b5b53")
            is_tall_card = h >= 85
            if is_tall_card:
                # Architectural card: crisp white surface, colored top accent strip, soft ambient shadow
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="13" fill="#ffffff" stroke="{accent_bar}" stroke-opacity="0.55" stroke-width="1.6" filter="url(#card-shadow)" />'
                )
                parts.append(
                    f'<path d="M {x+13:.1f} {y+0.8:.1f} H {x+w-13:.1f} Q {x+w-0.8:.1f} {y+0.8:.1f} {x+w-0.8:.1f} {y+13:.1f} V {y+18:.1f} H {x+0.8:.1f} V {y+13:.1f} Q {x+0.8:.1f} {y+0.8:.1f} {x+13:.1f} {y+0.8:.1f} Z" fill="{bg}" />'
                )
                parts.append(
                    f'<line x1="{x+14:.1f}" y1="{y+18:.1f}" x2="{x+w-14:.1f}" y2="{y+18:.1f}" stroke="{accent_bar}" stroke-opacity="0.28" stroke-width="1" />'
                )
            else:
                # Grid / data cell: refined architectural fill & thin crisp border
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="9" fill="{bg}" stroke="{accent_bar}" stroke-opacity="0.45" stroke-width="1.3" />'
                )
        elif kind == "ellipse":
            cx, cy = x + w / 2, y + h / 2
            rx, ry = w / 2, h / 2
            border_color = STROKE_PALETTE.get(bg, stroke)
            parts.append(
                f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{bg}" stroke="{border_color}" stroke-width="1.6" filter="url(#card-shadow)" />'
            )
        elif kind == "arrow":
            pts = [(x + px, y + py) for px, py in e.get("points", [])]
            if len(pts) >= 2:
                d_cmds = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
                for i in range(1, len(pts)):
                    d_cmds.append(f"L {pts[i][0]:.1f} {pts[i][1]:.1f}")
                d_str = " ".join(d_cmds)
                arrow_color = ACCENT if is_dashed else "#3e4c44"
                parts.append(
                    f'<path d="{d_str}" fill="none" stroke="{arrow_color}" stroke-width="{sw:.1f}" stroke-linecap="round" stroke-linejoin="round"{dash} />'
                )
                # Crisp filled triangular arrowhead
                (ax, ay), (bx, by) = pts[-2], pts[-1]
                ang = math.atan2(by - ay, bx - ax)
                hlen = 10.5
                a1 = ang + math.pi * 0.84
                a2 = ang - math.pi * 0.84
                hx1, hy1 = bx + math.cos(a1) * hlen, by + math.sin(a1) * hlen
                hx2, hy2 = bx + math.cos(a2) * hlen, by + math.sin(a2) * hlen
                parts.append(
                    f'<polygon points="{bx:.1f},{by:.1f} {hx1:.1f},{hy1:.1f} {hx2:.1f},{hy2:.1f}" fill="{arrow_color}" />'
                )
        elif kind == "text":
            txt = html.escape(str(e.get("text", "")))
            fsize = int(e.get("fontSize", 18))
            by = y + fsize * 0.92
            if fsize >= 22:
                cls, weight = "ed-title", "800"
            elif fsize >= 18:
                cls, weight = "ed-label", "700"
            elif fsize <= 14:
                cls, weight = "ed-mono", "600"
            else:
                cls, weight = "ed-label", "600"
            parts.append(
                f'<text x="{x:.1f}" y="{by:.1f}" font-size="{fsize}" font-weight="{weight}" fill="{stroke}" class="{cls}">{txt}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)
