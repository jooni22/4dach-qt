"""Refresh helpers that keep MainWindow state-change sequencing explicit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


DirtyStateMode = Literal["preserve", "refresh", "mark_saved"]


@dataclass(frozen=True, slots=True)
class PostStateChangeRefresh:
    """Contract for model mutations that should fan out through the main window.

    Order:
    1. optionally invalidate cached report HTML
    2. optionally refresh the material chooser
    3. refresh canvases and active-plane report/status facets
    4. update dirty indicators
    """

    invalidate_report_cache: bool = False
    refresh_materials: bool = False
    dirty_state_mode: DirtyStateMode = "preserve"


class _PostStateChangeRefreshTarget(Protocol):
    def _invalidate_cached_report(self) -> None: ...
    def _refresh_material_combo(self) -> None: ...
    def _refresh_canvas(self) -> None: ...
    def _mark_saved_state(self) -> None: ...
    def _refresh_dirty_state(self) -> None: ...


class _ActivePlaneFacetRefreshTarget(Protocol):
    def _sync_layout_direction_actions(self) -> None: ...
    def _apply_origin_edit_mode_to_canvases(self) -> None: ...
    def _refresh_active_canvas_selection_state(self) -> None: ...
    def _refresh_report(self) -> None: ...
    def _refresh_status_bar_info(self) -> None: ...


def apply_post_state_change_refresh(
    window: _PostStateChangeRefreshTarget,
    contract: PostStateChangeRefresh,
) -> None:
    if contract.invalidate_report_cache:
        window._invalidate_cached_report()
    if contract.refresh_materials:
        window._refresh_material_combo()
    window._refresh_canvas()
    if contract.dirty_state_mode == "mark_saved":
        window._mark_saved_state()
    elif contract.dirty_state_mode == "refresh":
        window._refresh_dirty_state()
    elif contract.dirty_state_mode != "preserve":
        raise ValueError(f"Unsupported dirty state mode: {contract.dirty_state_mode}")


def refresh_active_plane_facets(window: _ActivePlaneFacetRefreshTarget) -> None:
    window._sync_layout_direction_actions()
    window._apply_origin_edit_mode_to_canvases()
    window._refresh_active_canvas_selection_state()
    window._refresh_report()
    window._refresh_status_bar_info()
