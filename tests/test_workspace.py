from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QWidget

from ui.workspace import WorkspaceController


class _RecordingCanvas:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []

    def toggle_grid(self, enabled: bool) -> None:
        self.calls.append(("toggle_grid", enabled))

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        self.calls.append(("set_snap_to_grid_enabled", enabled))

    def set_sheet_visibility(self, visible: bool) -> None:
        self.calls.append(("set_sheet_visibility", visible))

    def update(self) -> None:
        self.calls.append(("update", None))


def _workspace_with_recording_canvases(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    workspace = WorkspaceController(parent, project_state=object(), get_material_fn=lambda _material_id: None)
    active_canvas = _RecordingCanvas()
    other_canvas = _RecordingCanvas()
    workspace.primary_canvas = active_canvas
    workspace._plane_tab_canvases = {"active": active_canvas, "other": other_canvas}
    return workspace, active_canvas, other_canvas


@pytest.mark.parametrize(
    ("method_name", "arg", "expected_call"),
    [
        ("toggle_grid", False, ("toggle_grid", False)),
        ("set_snap_to_grid_enabled", True, ("set_snap_to_grid_enabled", True)),
        ("set_sheet_visibility", False, ("set_sheet_visibility", False)),
    ],
)
def test_workspace_controller_propagates_canvas_operations_with_existing_primary_contract(
    qtbot,
    method_name: str,
    arg: bool,
    expected_call: tuple[str, object | None],
):
    workspace, active_canvas, other_canvas = _workspace_with_recording_canvases(qtbot)

    getattr(workspace, method_name)(arg)

    assert active_canvas.calls == [expected_call, expected_call]
    assert other_canvas.calls == [expected_call]


def test_workspace_controller_update_all_canvases_preserves_primary_first_fan_out(qtbot):
    workspace, active_canvas, other_canvas = _workspace_with_recording_canvases(qtbot)

    workspace.update_all_canvases()

    assert active_canvas.calls == [("update", None), ("update", None)]
    assert other_canvas.calls == [("update", None)]


def test_workspace_controller_set_sheet_visibility_updates_workspace_state(qtbot):
    workspace, _, _ = _workspace_with_recording_canvases(qtbot)
    assert workspace._sheets_visible is False

    workspace.set_sheet_visibility(False)

    assert workspace._sheets_visible is False


def test_workspace_controller_import_tab_is_not_a_plane_and_can_cancel(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    workspace = WorkspaceController(
        parent,
        project_state=object(),
        get_material_fn=lambda _material_id: None,
    )
    import_widget = QWidget()
    cancelled: list[bool] = []

    index = workspace.open_import_tab(
        import_widget,
        title="Import rzutu",
        on_cancel=lambda: cancelled.append(True),
    )

    assert workspace.tabs.tabText(index) == "Import rzutu"
    assert workspace.plane_id_for_tab_index(index) is None
    assert workspace.is_import_tab(index) is True
    assert workspace.import_tab_index() == index

    workspace.close_import_tab(cancel=True)

    assert cancelled == [True]
    assert workspace.import_tab_index() == -1
