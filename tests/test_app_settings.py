from __future__ import annotations

from core.app_settings import AppSettings


def test_default_value():
    s = AppSettings()
    assert s.partial_cutout_top_extra_cm == 15.0


def test_round_trip():
    s = AppSettings(partial_cutout_top_extra_cm=22.5)
    s2 = AppSettings.from_dict(s.to_dict())
    assert s2.partial_cutout_top_extra_cm == 22.5


def test_negative_clamped_to_zero():
    s = AppSettings.from_dict({"partial_cutout_top_extra_cm": -5.0})
    assert s.partial_cutout_top_extra_cm == 0.0


def test_invalid_type_uses_default():
    s = AppSettings.from_dict({"partial_cutout_top_extra_cm": "abc"})
    assert s.partial_cutout_top_extra_cm == 15.0


def test_missing_key_uses_default():
    s = AppSettings.from_dict({})
    assert s.partial_cutout_top_extra_cm == 15.0
