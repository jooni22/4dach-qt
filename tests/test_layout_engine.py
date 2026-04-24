from __future__ import annotations

from core.geometry import build_trapezoid_outline
from core.layout_engine import generate_layout
from core.models import Material, Point2D, Polygon2D, RoofPlane, almost_equal


def _material(**overrides) -> Material:
    payload = {
        "id": "TEST",
        "nazwa": "TEST",
        "type": "trapezowa",
        "effective_width_cm": 50,
        "min_sheet_length_cm": 10,
        "max_sheet_length_cm": 500,
        "top_margin_cm": 0,
        "bottom_margin_cm": 0,
    }
    payload.update(overrides)
    return Material(**payload)


def test_layout_engine_generates_deterministic_bands_for_simple_rectangle():
    plane = RoofPlane(id="plane-1", name="Rect", outline=Polygon2D.rectangle(120, 200))

    result = generate_layout(plane, _material())

    assert [(placement.band_index, placement.x_left_cm, placement.x_right_cm, placement.final_length_cm) for placement in result.placements] == [
        (0, 0.0, 50.0, 200.0),
        (1, 50.0, 100.0, 200.0),
        (2, 100.0, 120.0, 200.0),
    ]
    assert [band.band_index for band in result.bands] == [0, 1, 2]
    assert [(band.x_left_cm, band.x_right_cm, len(band.segments)) for band in result.bands] == [
        (0.0, 50.0, 1),
        (50.0, 100.0, 1),
        (100.0, 120.0, 1),
    ]
    assert [segment.raw_length_cm for band in result.bands for segment in band.segments] == [200.0, 200.0, 200.0]
    assert result.warnings == []


def test_layout_engine_splits_band_when_cutout_disconnects_vertical_strip():
    plane = RoofPlane(
        id="plane-1",
        name="Hole",
        outline=Polygon2D.rectangle(90, 100),
        holes=[Polygon2D.rectangle(30, 40, origin_x=30, origin_y=30)],
    )

    result = generate_layout(plane, _material(effective_width_cm=30))

    assert [(placement.band_index, placement.y_top_cm, placement.y_bottom_cm, placement.raw_length_cm) for placement in result.placements] == [
        (0, 0.0, 100.0, 100.0),
        (1, 0.0, 30.0, 30.0),
        (1, 70.0, 100.0, 30.0),
        (2, 0.0, 100.0, 100.0),
    ]
    assert len(result.bands[1].segments) == 2
    assert all(len(segment.coverage_polygons) == 1 for segment in result.bands[1].segments)


def test_layout_engine_keeps_connected_notched_band_as_one_segment_with_coverage_polygons():
    plane = RoofPlane(
        id="plane-1",
        name="Notch",
        outline=Polygon2D.rectangle(153, 200),
        holes=[Polygon2D.rectangle(30, 50, origin_x=60, origin_y=70)],
    )

    result = generate_layout(plane, _material(effective_width_cm=51))

    assert len(result.placements) == 3
    assert len(result.bands[1].segments) == 1
    assert len(result.bands[1].segments[0].coverage_polygons) == 4
    assert result.placements[1].x_left_cm == 51.0
    assert result.placements[1].x_right_cm == 102.0


def test_layout_engine_handles_trapezoid_strip_lengths():
    plane = RoofPlane(
        id="plane-1",
        name="Trap",
        outline=build_trapezoid_outline("równoramienny", 200, 100, 120),
    )

    result = generate_layout(plane, _material())

    assert [placement.final_length_cm for placement in result.placements] == [90.0, 120.0, 120.0, 90.0]
    assert almost_equal(result.placements[0].y_top_cm, 30.0)
    assert almost_equal(result.placements[-1].y_top_cm, 30.0)


def test_layout_engine_handles_irregular_polygon_without_qt_dependencies():
    plane = RoofPlane(
        id="plane-1",
        name="Irregular",
        outline=Polygon2D(
            [
                Point2D(0, 20),
                Point2D(40, 0),
                Point2D(90, 0),
                Point2D(120, 50),
                Point2D(100, 140),
                Point2D(30, 120),
                Point2D(0, 80),
            ]
        ),
    )

    result = generate_layout(plane, _material())

    assert len(result.placements) == 3
    assert [len(band.segments[0].coverage_polygons) for band in result.bands] == [3, 2, 1]
    assert result.placements[0].raw_length_cm < result.placements[1].raw_length_cm


def test_layout_engine_uses_envelope_for_skewed_band_lengths():
    """Slanted edges produce envelopes wider than any single cross-section.
    With a large enough max_sheet_length the sheet fits in one row."""
    plane = RoofPlane(
        id="plane-1",
        name="Skewed",
        outline=Polygon2D(
            [
                Point2D(0, 20),
                Point2D(120, 0),
                Point2D(120, 100),
                Point2D(0, 120),
            ]
        ),
    )

    result = generate_layout(plane, _material(max_sheet_length_cm=500))

    # The envelope for each band spans from min(top samples) to max(bottom samples),
    # so raw_length > 100 (the constant perpendicular span).
    assert len(result.placements) == 3
    for placement in result.placements:
        assert placement.raw_length_cm > 100.0
        assert placement.y_bottom_cm - placement.y_top_cm == placement.raw_length_cm


def test_layout_engine_tracks_multiple_cutouts_inside_band_coverage():
    plane = RoofPlane(
        id="plane-1",
        name="Multi",
        outline=Polygon2D.rectangle(150, 150),
        holes=[
            Polygon2D.rectangle(20, 40, origin_x=15, origin_y=20),
            Polygon2D.rectangle(20, 50, origin_x=65, origin_y=40),
            Polygon2D.rectangle(20, 30, origin_x=115, origin_y=60),
        ],
    )

    result = generate_layout(plane, _material())

    assert len(result.placements) == 3
    assert [len(band.segments[0].coverage_polygons) for band in result.bands] == [4, 4, 4]


def test_layout_engine_supports_layout_direction_change():
    plane = RoofPlane(id="plane-1", name="Direction", outline=Polygon2D.rectangle(120, 100))
    material = _material()

    left_result = generate_layout(plane, material)
    plane.generation_settings.layout_origin = "right"
    right_result = generate_layout(plane, material)

    assert [(placement.band_index, placement.x_left_cm, placement.x_right_cm) for placement in left_result.placements] == [
        (0, 0.0, 50.0),
        (1, 50.0, 100.0),
        (2, 100.0, 120.0),
    ]
    assert [(placement.band_index, placement.x_left_cm, placement.x_right_cm) for placement in right_result.placements] == [
        (0, 70.0, 120.0),
        (1, 20.0, 70.0),
        (2, 0.0, 20.0),
    ]


def test_layout_engine_validates_min_and_max_sheet_length_edges():
    plane = RoofPlane(
        id="plane-1",
        name="Edges",
        outline=Polygon2D.rectangle(100, 150),
        holes=[Polygon2D.rectangle(50, 90, origin_x=0, origin_y=30)],
    )
    material = _material(effective_width_cm=50, min_sheet_length_cm=80, max_sheet_length_cm=120)

    result = generate_layout(plane, material)

    # Band 1 (no hole): raw=150, final=150 > max=120 → split into rows 120+30.
    # Row 2 (raw=30, final=30) is below min_sheet_length=80 → rejected.
    assert [(p.band_index, p.final_length_cm) for p in result.placements] == [
        (1, 120.0),
    ]
    assert [(segment.band_index, segment.raw_length_cm, segment.reason) for segment in result.rejected_segments] == [
        (0, 30.0, "below_min_length"),
        (0, 30.0, "below_min_length"),
        (1, 30.0, "below_min_length"),
    ]


def test_layout_engine_transverse_split_for_large_rectangle():
    """A 1000x1000 rectangle with max_sheet_length=900 splits into 2 rows."""
    plane = RoofPlane(
        id="plane-1",
        name="Large",
        outline=Polygon2D.rectangle(100, 1000),
    )
    material = _material(
        effective_width_cm=50,
        max_sheet_length_cm=900,
        min_sheet_length_cm=10,
        top_margin_cm=0,
        bottom_margin_cm=0,
    )

    result = generate_layout(plane, material)

    # 2 bands × 2 rows each = 4 placements.
    assert len(result.placements) == 4
    # Each band: row-0 = 900, row-1 = 100.
    band_0 = [p for p in result.placements if p.band_index == 0]
    assert [p.final_length_cm for p in band_0] == [900.0, 100.0]
    assert [p.y_top_cm for p in band_0] == [0.0, 900.0]
    assert [p.y_bottom_cm for p in band_0] == [900.0, 1000.0]


def test_layout_engine_transverse_split_with_margins():
    """Margins reduce max coverage per row, so a 1000cm height with 50+50 margins
    on a max=900 sheet splits into rows of 800 coverage + 200 coverage."""
    plane = RoofPlane(
        id="plane-1",
        name="Margins",
        outline=Polygon2D.rectangle(50, 1000),
    )
    material = _material(
        effective_width_cm=50,
        max_sheet_length_cm=900,
        min_sheet_length_cm=10,
        top_margin_cm=50,
        bottom_margin_cm=50,
    )

    result = generate_layout(plane, material)

    # raw=1000, final=1000+100=1100 > max=900.
    # max_coverage = 900 - 100 = 800 per row.
    # Row 0: raw=800, final=800+100=900.
    # Row 1: raw=200, final=200+100=300.
    assert len(result.placements) == 2
    assert [p.final_length_cm for p in result.placements] == [900.0, 300.0]
    assert [p.raw_length_cm for p in result.placements] == [800.0, 200.0]
    assert [p.y_top_cm for p in result.placements] == [0.0, 800.0]
    assert [p.y_bottom_cm for p in result.placements] == [800.0, 1000.0]
