from __future__ import annotations

from core.geometry import build_trapezoid_outline
from core.layout_engine import EPSILON, generate_layout
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

    assert [placement.final_length_cm for placement in result.placements] == [120.0, 120.0, 120.0, 120.0]
    assert almost_equal(result.placements[0].y_top_cm, 0.0)
    assert almost_equal(result.placements[-1].y_top_cm, 0.0)


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


def test_layout_engine_uses_single_cross_section_for_skewed_band_lengths():
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

    result = generate_layout(plane, _material(max_sheet_length_cm=100, min_sheet_length_cm=0))

    expected_lengths = [100.0, 8.333333333333334, 100.0, 8.33333333333334, 100.0, 3.3333333333333286]
    assert len(result.placements) == len(expected_lengths)
    for p, exp in zip(result.placements, expected_lengths):
        assert almost_equal(p.raw_length_cm, exp)
        assert almost_equal(p.final_length_cm, exp)
    assert result.requires_transverse_split is False


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

    assert [(placement.band_index, placement.final_length_cm, placement.split_reason) for placement in result.placements] == [
        (1, 120.0, None),
    ]
    assert len(result.rejected_segments) == 3

def test_layout_engine_cutout_intersection_count():
    # Prostokąt 1000x1000
    outline = Polygon2D.rectangle(1000, 1000)
    # Wycinek 300x300 na środku, czyli od x=350 do x=650
    hole = Polygon2D.rectangle(300, 300, origin_x=350, origin_y=350)
    plane = RoofPlane(id="p1", name="Test", outline=outline, holes=[hole])
    
    # Szerokość arkusza 51 cm
    mat = _material(effective_width_cm=51, module_length_cm=0, max_sheet_length_cm=2000)
    result = generate_layout(plane, mat)
    
    # Sprawdzamy ile pasów zostało przeciętych przez wycinek
    # Wycinek jest od x=350 do x=650. 
    # Pasy szerokości 51cm:
    # 350 / 51 = 6.86 -> pas nr 6 (zaczyna się od 306, kończy na 357). Przecięty!
    # 650 / 51 = 12.74 -> pas nr 12 (zaczyna się od 612, kończy na 663). Przecięty!
    # Pasy dotknięte przez wycinek to indeksy od 6 do 12 włącznie, czyli 7 pasów.
    
    # Kiedy pas jest przecięty, ma więcej niż 1 segment (czyli generuje więcej niż 1 placement dla danego band_index)
    placements_by_band = {}
    for p in result.placements:
        placements_by_band.setdefault(p.band_index, []).append(p)
        
    intersected_bands = [
        band_index 
        for band_index, pl_list in placements_by_band.items() 
        if len(pl_list) > 1
    ]
    
    assert intersected_bands == [7, 8, 9, 10, 11]


def test_partial_cutout_one_segment_annotated():
    """Band partially covered by hole → 1 segment, cutout_interaction='partial'."""
    # Outline: 100×1000, band width=50cm → band 0 is x=0..50
    # Hole: x=10..40, y=400..600 — doesn't cover full band width (0..50)
    plane = RoofPlane(
        id="plane-1",
        name="Partial",
        outline=Polygon2D.rectangle(100, 1000),
        holes=[Polygon2D.rectangle(30, 200, origin_x=10, origin_y=400)],
    )
    result = generate_layout(plane, _material(effective_width_cm=50, max_sheet_length_cm=2000))

    # Band 0 should have 1 segment (partial cutout keeps it as one piece)
    band0 = result.bands[0]
    assert len(band0.segments) == 1
    seg = band0.segments[0]
    assert seg.cutout_interaction == "partial"
    assert seg.partial_cut_line_y_cm == 400.0  # top edge of the hole


def test_full_cutout_two_segments():
    """Band fully covered by hole → 2 segments (above and below hole)."""
    # Hole x=0..50 covers the entire band width
    plane = RoofPlane(
        id="plane-1",
        name="Full",
        outline=Polygon2D.rectangle(100, 1000),
        holes=[Polygon2D.rectangle(50, 200, origin_x=0, origin_y=400)],
    )
    result = generate_layout(plane, _material(effective_width_cm=50, max_sheet_length_cm=2000))

    band0 = result.bands[0]
    assert len(band0.segments) == 2
    for seg in band0.segments:
        assert seg.cutout_interaction == "full"


def test_partial_cutout_top_extra_applied():
    """top_extra_cm from settings is reflected in final_length_cm of the sheet."""
    from core.app_settings import AppSettings

    plane = RoofPlane(
        id="plane-1",
        name="Extra",
        outline=Polygon2D.rectangle(100, 1000),
        holes=[Polygon2D.rectangle(30, 200, origin_x=10, origin_y=400)],
    )
    settings = AppSettings(partial_cutout_top_extra_cm=20.0)
    result = generate_layout(plane, _material(effective_width_cm=50, max_sheet_length_cm=2000), settings=settings)

    # Find the placement with split_reason="partial_cutout"
    partial_placements = [p for p in result.placements if p.split_reason == "partial_cutout"]
    assert len(partial_placements) == 1
    p = partial_placements[0]
    assert p.final_length_cm == p.raw_length_cm + 20.0


def test_partial_cutout_top_extra_clamped():
    """top_extra_cm cannot exceed the distance from segment top to cut line."""
    from core.app_settings import AppSettings

    # Hole starts at y=10 in a 1000-high outline → cut_y=10
    # segment.y_top_cm = 0 → max_extra = 10 - 0 = 10
    plane = RoofPlane(
        id="plane-1",
        name="Clamp",
        outline=Polygon2D.rectangle(100, 1000),
        holes=[Polygon2D.rectangle(30, 200, origin_x=10, origin_y=10)],
    )
    settings = AppSettings(partial_cutout_top_extra_cm=999.0)
    result = generate_layout(plane, _material(effective_width_cm=50, max_sheet_length_cm=2000), settings=settings)

    band0 = result.bands[0]
    seg = band0.segments[0]
    assert seg.cutout_interaction == "partial"
    assert seg.top_extra_cm <= seg.partial_cut_line_y_cm - seg.y_top_cm + EPSILON


def test_generate_layout_backward_compatible():
    """generate_layout(plane, material) without settings still works."""
    plane = RoofPlane(id="plane-1", name="Compat", outline=Polygon2D.rectangle(120, 200))
    result = generate_layout(plane, _material())
    assert len(result.placements) == 3
    assert result.warnings == []

