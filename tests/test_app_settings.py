from __future__ import annotations

from core.app_settings import AppSettings, LIVE_ANGLE_MODE_RELATIVE_TO_PREV


def test_default_value():
    s = AppSettings()
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.shift_drag_behavior == "free_move"
    assert s.show_axis_overlay is True
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10
    assert s.show_crosshair is True
    assert s.live_angle_mode == "absolute"
    assert s.show_decimal_cm is False
    assert s.show_angle_arc is True
    assert s.show_guide_lines is True
    assert s.close_on_rmb is True


def test_round_trip():
    s = AppSettings(
        partial_cutout_top_extra_cm=22.5,
        grid_size_cm=25.0,
        shift_drag_behavior="orthogonal_lock",
        show_axis_overlay=False,
        grid_major_cm=50,
        grid_minor_cm=5,
        show_crosshair=False,
        live_angle_mode=LIVE_ANGLE_MODE_RELATIVE_TO_PREV,
        show_decimal_cm=True,
        show_angle_arc=False,
        show_guide_lines=False,
        close_on_rmb=False,
        snap_to_grid=False,
        snap_to_axis=False,
        snap_to_45deg=False,
        snap_to_3060deg=True,
        snap_to_points=False,
        show_inferences=False,
        snap_axis_threshold_deg=4.0,
        snap_45_threshold_deg=3.5,
        snap_radius_px=18,
    )
    s2 = AppSettings.from_dict(s.to_dict())
    assert s2.partial_cutout_top_extra_cm == 22.5
    assert s2.grid_size_cm == 25.0
    assert s2.shift_drag_behavior == "orthogonal_lock"
    assert s2.show_axis_overlay is False
    assert s2.grid_major_cm == 50
    assert s2.grid_minor_cm == 5
    assert s2.show_crosshair is False
    assert s2.live_angle_mode == LIVE_ANGLE_MODE_RELATIVE_TO_PREV
    assert s2.show_decimal_cm is True
    assert s2.show_angle_arc is False
    assert s2.show_guide_lines is False
    assert s2.close_on_rmb is False
    assert s2.snap_to_grid is False
    assert s2.snap_to_axis is False
    assert s2.snap_to_45deg is False
    assert s2.snap_to_3060deg is True
    assert s2.snap_to_points is False
    assert s2.show_inferences is False
    assert s2.snap_axis_threshold_deg == 4.0
    assert s2.snap_45_threshold_deg == 3.5
    assert s2.snap_radius_px == 18


def test_negative_clamped_to_zero():
    s = AppSettings.from_dict({"partial_cutout_top_extra_cm": -5.0})
    assert s.partial_cutout_top_extra_cm == 0.0


def test_invalid_type_uses_default():
    s = AppSettings.from_dict(
        {
            "partial_cutout_top_extra_cm": "abc",
            "grid_size_cm": "abc",
            "grid_major_cm": "abc",
            "grid_minor_cm": "abc",
            "snap_axis_threshold_deg": "abc",
            "snap_45_threshold_deg": "abc",
            "snap_radius_px": "abc",
        }
    )
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10
    assert s.snap_axis_threshold_deg == 3.0
    assert s.snap_45_threshold_deg == 2.5
    assert s.snap_radius_px == 12


def test_missing_key_uses_default():
    s = AppSettings.from_dict({})
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.show_axis_overlay is True
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10
    assert s.show_crosshair is True
    assert s.live_angle_mode == "absolute"
    assert s.show_decimal_cm is False
    assert s.show_angle_arc is True
    assert s.show_guide_lines is True
    assert s.close_on_rmb is True


def test_nonpositive_grid_size_uses_default():
    s = AppSettings.from_dict({"grid_size_cm": 0, "grid_major_cm": 0, "grid_minor_cm": -1})
    assert s.grid_size_cm == 10.0
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10


def test_invalid_shift_drag_behavior_uses_default():
    s = AppSettings.from_dict({"shift_drag_behavior": "diagonal_rocket"})
    assert s.shift_drag_behavior == "free_move"


def test_invalid_live_angle_mode_uses_default():
    s = AppSettings.from_dict({"live_angle_mode": "chaos"})
    assert s.live_angle_mode == "absolute"


def test_nonpositive_snap_thresholds_use_defaults():
    s = AppSettings.from_dict(
        {
            "snap_axis_threshold_deg": 0,
            "snap_45_threshold_deg": -1,
            "snap_radius_px": 0,
        }
    )
    assert s.snap_axis_threshold_deg == 3.0
    assert s.snap_45_threshold_deg == 2.5
    assert s.snap_radius_px == 12
