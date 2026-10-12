"""Tiny vision analysis for the Eyes feature — stdlib only.

The dashboard captures phone-camera frames, downsamples to 48x36 grayscale
on a canvas, and POSTs raw bytes as base64. This module decodes and reduces
each frame to three honest signals:

- brightness: mean pixel value, 0 (black) .. 1 (white)
- motion: mean absolute per-pixel difference vs the previous frame, 0..1
- zones: a coarse 3x3 brightness map (row-major, each 0..1)

No ML, no models, no dependencies — just arithmetic on 1728 bytes.
"""
from __future__ import annotations


def analyze_frame(px: bytes, w: int, h: int, prev: bytes | None):
    """Return (brightness, motion, zones). Raises ValueError on bad input."""
    if w <= 0 or h <= 0 or w * h > 65536:
        raise ValueError("bad frame dimensions")
    if len(px) != w * h:
        raise ValueError(f"expected {w*h} bytes, got {len(px)}")
    n = len(px)
    brightness = sum(px) / (n * 255.0)

    motion = 0.0
    if prev is not None and len(prev) == n:
        diff = sum(abs(a - b) for a, b in zip(px, prev))
        motion = diff / (n * 255.0)

    # 3x3 zone brightness map.
    zones: list[float] = []
    for zy in range(3):
        for zx in range(3):
            total = 0
            count = 0
            y0, y1 = (zy * h) // 3, ((zy + 1) * h) // 3
            x0, x1 = (zx * w) // 3, ((zx + 1) * w) // 3
            for y in range(y0, y1):
                row = y * w
                for x in range(x0, x1):
                    total += px[row + x]
                    count += 1
            zones.append(round(total / (count * 255.0), 3) if count else 0.0)

    return round(brightness, 3), round(motion, 3), zones


def scene_signature(brightness: float, motion: float, zones: list[float],
                    hour: int) -> str:
    """Coarse, stable signature used for scene recognition.

    Buckets: brightness -> 5 levels, motion -> 4 levels, each zone -> 3
    levels, plus hour of day. Two frames of the "same place" should land
    on the same signature; small lighting wiggles stay in-bucket.
    """
    b = min(4, int(brightness * 5))
    m = min(3, int(motion * 4))
    z = "".join(str(min(2, int(v * 3))) for v in zones)
    return f"b{b}m{m}z{z}h{hour:02d}"
