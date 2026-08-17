"""Generate the mini program tab bar PNG icons without external dependencies."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib


SIZE = 81
SCALE = 4
CANVAS_SIZE = SIZE * SCALE
NORMAL = (135, 145, 136)
ACTIVE = (47, 125, 74)
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "miniapp" / "src" / "static" / "tabbar"


class Canvas:
    def __init__(self, color: tuple[int, int, int]) -> None:
        self.color = color
        self.alpha = bytearray(CANVAS_SIZE * CANVAS_SIZE)

    def _paint(self, x: int, y: int) -> None:
        if 0 <= x < CANVAS_SIZE and 0 <= y < CANVAS_SIZE:
            self.alpha[y * CANVAS_SIZE + x] = 255

    def line(self, start: tuple[float, float], end: tuple[float, float], width: float = 4.5) -> None:
        x1, y1 = (value * SCALE for value in start)
        x2, y2 = (value * SCALE for value in end)
        radius = width * SCALE / 2
        min_x = max(0, int(min(x1, x2) - radius - 1))
        max_x = min(CANVAS_SIZE - 1, int(max(x1, x2) + radius + 1))
        min_y = max(0, int(min(y1, y2) - radius - 1))
        max_y = min(CANVAS_SIZE - 1, int(max(y1, y2) + radius + 1))
        dx, dy = x2 - x1, y2 - y1
        length_squared = dx * dx + dy * dy
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if length_squared:
                    ratio = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length_squared))
                    nearest_x, nearest_y = x1 + ratio * dx, y1 + ratio * dy
                else:
                    nearest_x, nearest_y = x1, y1
                if math.hypot(x - nearest_x, y - nearest_y) <= radius:
                    self._paint(x, y)

    def polyline(self, points: list[tuple[float, float]], width: float = 4.5) -> None:
        for start, end in zip(points, points[1:]):
            self.line(start, end, width)

    def circle(self, center: tuple[float, float], radius: float, width: float = 4.5) -> None:
        cx, cy = (value * SCALE for value in center)
        outer = (radius + width / 2) * SCALE
        inner = max(0, (radius - width / 2) * SCALE)
        for y in range(max(0, int(cy - outer - 1)), min(CANVAS_SIZE, int(cy + outer + 2))):
            for x in range(max(0, int(cx - outer - 1)), min(CANVAS_SIZE, int(cx + outer + 2))):
                distance = math.hypot(x - cx, y - cy)
                if inner <= distance <= outer:
                    self._paint(x, y)

    def arc(
        self,
        center: tuple[float, float],
        radius: float,
        start_degrees: int,
        end_degrees: int,
        width: float = 4.5,
    ) -> None:
        points = []
        for degrees in range(start_degrees, end_degrees + 1, 2):
            radians = math.radians(degrees)
            points.append((center[0] + radius * math.cos(radians), center[1] + radius * math.sin(radians)))
        self.polyline(points, width)

    def png_bytes(self) -> bytes:
        rgba_rows = []
        red, green, blue = self.color
        for output_y in range(SIZE):
            row = bytearray([0])
            for output_x in range(SIZE):
                total_alpha = 0
                for sub_y in range(SCALE):
                    offset = (output_y * SCALE + sub_y) * CANVAS_SIZE + output_x * SCALE
                    total_alpha += sum(self.alpha[offset : offset + SCALE])
                alpha = round(total_alpha / (SCALE * SCALE))
                row.extend((red, green, blue, alpha))
            rgba_rows.append(bytes(row))
        raw = b"".join(rgba_rows)

        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

        signature = b"\x89PNG\r\n\x1a\n"
        header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
        return signature + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def draw_home(canvas: Canvas) -> None:
    canvas.polyline([(16, 40), (40.5, 18), (65, 40)])
    canvas.polyline([(22, 36), (22, 64), (59, 64), (59, 36)])
    canvas.polyline([(34, 64), (34, 48), (47, 48), (47, 64)])


def draw_inventory(canvas: Canvas) -> None:
    canvas.polyline([(17, 29), (40.5, 18), (64, 29), (64, 63), (17, 63), (17, 29)])
    canvas.polyline([(17, 29), (40.5, 41), (64, 29)])
    canvas.line((40.5, 41), (40.5, 63))


def draw_recipe(canvas: Canvas) -> None:
    canvas.line((18, 39), (63, 39))
    canvas.polyline([(22, 39), (24, 61), (57, 61), (59, 39)])
    canvas.line((31, 30), (50, 30))
    canvas.line((37, 23), (44, 23))
    canvas.line((40.5, 20), (40.5, 27))
    canvas.line((64, 18), (64, 30), 3.5)
    canvas.line((58, 24), (70, 24), 3.5)


def draw_history(canvas: Canvas) -> None:
    canvas.circle((40.5, 41), 24)
    canvas.line((40.5, 41), (40.5, 27))
    canvas.line((40.5, 41), (52, 48))


def draw_profile(canvas: Canvas) -> None:
    canvas.circle((40.5, 28), 10)
    canvas.arc((40.5, 65), 23, 200, 340)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    icons = {
        "home": draw_home,
        "inventory": draw_inventory,
        "recipe": draw_recipe,
        "history": draw_history,
        "profile": draw_profile,
    }
    for name, draw in icons.items():
        for suffix, color in (("", NORMAL), ("-active", ACTIVE)):
            canvas = Canvas(color)
            draw(canvas)
            (OUTPUT_DIR / f"{name}{suffix}.png").write_bytes(canvas.png_bytes())


if __name__ == "__main__":
    main()
