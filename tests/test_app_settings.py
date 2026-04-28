from __future__ import annotations

from core.app_settings import AppSettings


def test_default_value():
    s = AppSettings()
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.shift_drag_behavior == "free_move"
    assert s.show_axis_overlay is True
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10
    assert s.show_crosshair is True


def test_round_trip():
    s = AppSettings(
        partial_cutout_top_extra_cm=22.5,
        grid_size_cm=25.0,
        shift_drag_behavior="orthogonal_lock",
        show_axis_overlay=False,
        grid_major_cm=50,
        grid_minor_cm=5,
        show_crosshair=False,
    )
    s2 = AppSettings.from_dict(s.to_dict())
    assert s2.partial_cutout_top_extra_cm == 22.5
    assert s2.grid_size_cm == 25.0
    assert s2.shift_drag_behavior == "orthogonal_lock"
    assert s2.show_axis_overlay is False
    assert s2.grid_major_cm == 50
    assert s2.grid_minor_cm == 5
    assert s2.show_crosshair is False


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
        }
    )
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10


def test_missing_key_uses_default():
    s = AppSettings.from_dict({})
    assert s.partial_cutout_top_extra_cm == 15.0
    assert s.grid_size_cm == 10.0
    assert s.show_axis_overlay is True
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10
    assert s.show_crosshair is True


def test_nonpositive_grid_size_uses_default():
    s = AppSettings.from_dict({"grid_size_cm": 0, "grid_major_cm": 0, "grid_minor_cm": -1})
    assert s.grid_size_cm == 10.0
    assert s.grid_major_cm == 100
    assert s.grid_minor_cm == 10


def test_invalid_shift_drag_behavior_uses_default():
    s = AppSettings.from_dict({"shift_drag_behavior": "diagonal_rocket"})
    assert s.shift_drag_behavior == "free_move"
