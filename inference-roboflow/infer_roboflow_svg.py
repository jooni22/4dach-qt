from __future__ import annotations

import argparse
import html
import os
import struct
from pathlib import Path
from typing import Any

from inference_sdk import InferenceHTTPClient

DEFAULT_API_URL = "https://serverless.roboflow.com"
DEFAULT_MODEL_ID = "roof-plan-strict-clean/2"
DEFAULT_API_KEY = "PofvpbO277Fof3GFUXU4"

SVG_COLORS = [
    "#E63946",
    "#2A9D8F",
    "#457B9D",
    "#F77F00",
    "#6D597A",
    "#118AB2",
    "#8AC926",
    "#B5179E",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Roboflow roof segmentation and write only one SVG next to the image."
    )
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("1.jpg"),
        help="Input image path. Defaults to 1.jpg next to this script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional SVG output path. Defaults to input image with .svg suffix.",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Roboflow model id.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Roboflow inference API URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ROBOFLOW_API_KEY", DEFAULT_API_KEY),
        help="Roboflow API key. Can also be set with ROBOFLOW_API_KEY.",
    )
    return parser.parse_args()


def read_png_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as file:
        header = file.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def read_jpeg_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as file:
        if file.read(2) != b"\xff\xd8":
            return None
        while True:
            marker_prefix = file.read(1)
            if not marker_prefix:
                return None
            if marker_prefix != b"\xff":
                continue
            marker = file.read(1)
            while marker == b"\xff":
                marker = file.read(1)
            if marker in {b"\xd8", b"\xd9"}:
                continue
            length_bytes = file.read(2)
            if len(length_bytes) != 2:
                return None
            segment_length = struct.unpack(">H", length_bytes)[0]
            if marker in {
                b"\xc0",
                b"\xc1",
                b"\xc2",
                b"\xc3",
                b"\xc5",
                b"\xc6",
                b"\xc7",
                b"\xc9",
                b"\xca",
                b"\xcb",
                b"\xcd",
                b"\xce",
                b"\xcf",
            }:
                data = file.read(5)
                if len(data) != 5:
                    return None
                height, width = struct.unpack(">HH", data[1:5])
                return int(width), int(height)
            file.seek(segment_length - 2, 1)


def read_image_size(path: Path) -> tuple[int, int] | None:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return read_png_size(path)
    if suffix in {".jpg", ".jpeg"}:
        return read_jpeg_size(path)
    return None


def points_from_prediction(prediction: dict[str, Any]) -> list[tuple[float, float]]:
    points = prediction.get("points", [])
    if not isinstance(points, list):
        return []

    parsed: list[tuple[float, float]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        x = point.get("x")
        y = point.get("y")
        if isinstance(x, int | float) and isinstance(y, int | float):
            parsed.append((float(x), float(y)))
    return parsed


def image_size_from_result(result: dict[str, Any], image_path: Path) -> tuple[int, int]:
    image = result.get("image", {})
    if isinstance(image, dict):
        width = image.get("width")
        height = image.get("height")
        if isinstance(width, int | float) and isinstance(height, int | float):
            return int(width), int(height)

    fallback_size = read_image_size(image_path)
    if fallback_size is None:
        raise ValueError("Could not determine image size from Roboflow result or image file.")
    return fallback_size


def format_points(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def label_position(points: list[tuple[float, float]]) -> tuple[float, float]:
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def build_svg(result: dict[str, Any], image_path: Path) -> str:
    width, height = image_size_from_result(result, image_path)
    raw_predictions = result.get("predictions", [])
    predictions = raw_predictions if isinstance(raw_predictions, list) else []

    groups: list[str] = []
    segment_index = 0
    for prediction in predictions:
        if not isinstance(prediction, dict):
            continue
        points = points_from_prediction(prediction)
        if not points:
            continue

        segment_index += 1
        color = SVG_COLORS[(segment_index - 1) % len(SVG_COLORS)]
        confidence = prediction.get("confidence")
        class_name = str(prediction.get("class", "roof-segment"))
        confidence_attr = ""
        confidence_label = ""
        if isinstance(confidence, int | float):
            confidence_attr = f' data-confidence="{float(confidence):.6f}"'
            confidence_label = f" {float(confidence):.3f}"
        text_x, text_y = label_position(points)
        title = html.escape(f"segment-{segment_index:03d} {class_name}{confidence_label}")
        groups.append(
            "\n".join(
                [
                    f'<g id="segment-{segment_index:03d}" class="roof-segment"{confidence_attr}>',
                    f"<title>{title}</title>",
                    (
                        f'<polygon points="{html.escape(format_points(points), quote=True)}" '
                        f'fill="{color}" fill-opacity="0.28" stroke="{color}" '
                        'stroke-width="3" vector-effect="non-scaling-stroke"/>'
                    ),
                    (
                        f'<text x="{text_x:.1f}" y="{text_y:.1f}" '
                        'font-family="Arial, sans-serif" font-size="18" '
                        'text-anchor="middle" paint-order="stroke" stroke="white" '
                        'stroke-width="4" fill="#111827">'
                        f"{segment_index}</text>"
                    ),
                    "</g>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            ),
            "<style>.roof-segment text{pointer-events:none}</style>",
            *groups,
            "</svg>",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    image_path = args.image.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")

    output_path = (
        args.output.expanduser().resolve()
        if args.output
        else image_path.with_suffix(".svg")
    )
    client = InferenceHTTPClient(api_url=args.api_url, api_key=args.api_key)
    result = client.infer(str(image_path), model_id=args.model_id)
    output_path.write_text(build_svg(result, image_path), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
