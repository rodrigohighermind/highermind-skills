"""Pixel parity of the window title bar against a reference product, measured, not eyeballed.

Usage: python3 tools/design_parity.py <ours.png> <reference.png>
Both are 2x window captures (screencapture -o -l <id>). The same measurement runs on both (no
hand-typed numbers): elements are blobs differing from the title-bar background, left ones from the
left edge, right ones from the right edge, in points. Fails (exit 1) when any element is off by more
than TOLERANCE_PT. Counterproof: the reference against itself must PASS.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image

TOLERANCE_PT = 1.0
Box = dict[str, float]


def blobs(img: Image.Image, box: tuple[int, int, int, int], min_px: int = 60) -> list[tuple[float, float, float, float]]:
    """(cx, cy, w, h) in points of blobs differing from the region's median color."""
    x0, y0, _x1, _y1 = box
    region = img.crop(box).convert("RGB")
    w, h = region.size
    px = region.load()
    colors = sorted(px[x, y] for x in range(0, w, 4) for y in range(0, h, 4))
    bg = colors[len(colors) // 2]
    def differs(c: tuple[int, int, int]) -> bool:
        return sum(abs(a - b) for a, b in zip(c, bg, strict=True)) > 30
    seen = [[False] * w for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or not differs(px[x, y]):
                continue
            q, pts = deque([(x, y)]), []
            seen[y][x] = True
            while q:
                cx, cy = q.popleft()
                pts.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1),
                               (cx + 2, cy), (cx - 2, cy), (cx, cy + 2), (cx, cy - 2)):  # bridge thin strokes
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and differs(px[nx, ny]):
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if len(pts) >= min_px:
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                out.append(((x0 + (min(xs) + max(xs)) / 2) / 2, (y0 + (min(ys) + max(ys)) / 2) / 2,
                            (max(xs) - min(xs) + 1) / 2, (max(ys) - min(ys) + 1) / 2))
    return sorted(out)


def measure(path: Path) -> dict[str, list[Box]]:
    """Title-bar elements of a 2x window capture: left (lights + toggle) from the left edge,
    right icons from the right edge, all in points."""
    img = Image.open(path)
    width_pt = img.size[0] / 2
    left = [b for b in blobs(img, (20, 16, 260, 74)) if b[2] >= 8]  # skip the rounded corner
    right = [b for b in blobs(img, (img.size[0] - 240, 16, img.size[0] - 16, 74)) if b[2] >= 8]
    return {
        "left": [{"cx": b[0], "cy": b[1], "w": b[2]} for b in left],
        "right": sorted(({"cx": round(width_pt - b[0], 2), "cy": b[1], "w": b[2]} for b in right),
                        key=lambda d: -d["cx"]),
    }


def compare(ref: dict[str, list[Box]], got: dict[str, list[Box]]) -> list[str]:
    fails: list[str] = []
    for side in ("left", "right"):
        if len(ref[side]) != len(got[side]):
            fails.append(f"{side}: {len(got[side])} elements, reference has {len(ref[side])}")
        for i, (r, g) in enumerate(zip(ref[side], got[side], strict=False)):
            for k in ("cx", "cy", "w"):
                if abs(r[k] - g[k]) > TOLERANCE_PT:
                    fails.append(f"{side}[{i}].{k}: {g[k]:.2f} pt vs reference {r[k]:.2f} pt")
    return fails


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: design_parity.py <ours.png> <reference.png>")
        sys.exit(2)
    ours, ref = measure(Path(sys.argv[1])), measure(Path(sys.argv[2]))
    print("reference:", json.dumps(ref))
    print("ours:     ", json.dumps(ours))
    problems = compare(ref, ours)
    print("PARITY PASS" if not problems else "PARITY FAIL\n  " + "\n  ".join(problems))
    sys.exit(1 if problems else 0)
