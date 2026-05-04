from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
PNG_PATH = ASSETS_DIR / "app_icon.png"
ICO_PATH = ASSETS_DIR / "app_icon.ico"

ROOF_COLOR = "#cc743d"


def _scale_points(size: int, points: list[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(round(x * size / 512), round(y * size / 512)) for x, y in points]


def _draw_row(draw: ImageDraw.ImageDraw, size: int, points: list[tuple[float, float]]) -> None:
    draw.polygon(_scale_points(size, points), fill=ROOF_COLOR)


def _draw_window(draw: ImageDraw.ImageDraw, size: int, x: float, y: float, w: float, h: float) -> None:
    x0 = round(x * size / 512)
    y0 = round(y * size / 512)
    x1 = round((x + w) * size / 512)
    y1 = round((y + h) * size / 512)
    draw.rectangle((x0, y0, x1, y1), fill=ROOF_COLOR)


def _draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    _draw_row(
        draw,
        size,
        [
            (24, 350), (54, 326), (78, 332), (100, 320), (124, 327), (146, 315),
            (169, 322), (192, 309), (223, 319), (243, 301), (223, 293), (196, 305),
            (176, 297), (154, 309), (131, 301), (107, 313), (85, 305), (63, 317),
            (47, 312), (12, 340),
        ],
    )
    _draw_row(
        draw,
        size,
        [
            (54, 300), (81, 279), (102, 285), (120, 275), (140, 281), (158, 271),
            (177, 277), (195, 267), (220, 275), (236, 261), (220, 254), (198, 263),
            (182, 257), (164, 267), (145, 261), (125, 271), (107, 265), (89, 275),
            (76, 271), (45, 296),
        ],
    )
    _draw_row(
        draw,
        size,
        [
            (88, 254), (114, 233), (134, 239), (152, 229), (171, 235), (189, 225),
            (207, 231), (225, 221), (248, 229), (264, 215), (248, 209), (228, 218),
            (211, 212), (193, 222), (175, 216), (156, 226), (138, 220), (120, 230),
            (107, 226), (78, 250),
        ],
    )

    draw.polygon(
        _scale_points(size, [(18, 367), (180, 367), (354, 197), (466, 308), (491, 308), (354, 171)]),
        fill=ROOF_COLOR,
    )
    draw.polygon(_scale_points(size, [(417, 179), (446, 179), (446, 241), (417, 212)]), fill=ROOF_COLOR)

    for x, y in ((321, 292), (347, 292), (321, 318), (347, 318)):
        _draw_window(draw, size, x, y, 18, 18)

    return image


def main() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    png = _draw_icon(256)
    png.save(PNG_PATH)

    icon = _draw_icon(256)
    icon.save(ICO_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


if __name__ == "__main__":
    main()
