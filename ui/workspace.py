"""workspace.py — WorkspaceController manages the central QTabWidget.

Responsibilities:
- Building per-plane tabs with DrawingCanvases
- Keeping tabs in sync with ProjectState
- Propagating active-plane changes to the rest of the window
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ui.drawing_canvas import DrawingCanvas


class WorkspaceController:
    """Owns the QTabWidget and the per-plane DrawingCanvas instances."""

    def __init__(self, parent: QWidget, project_state, get_material_fn) -> None:
        self._project_state = project_state
        self._get_material = get_material_fn
        self._plane_tab_canvases: dict[str, DrawingCanvas] = {}

        self.tabs = QTabWidget(parent)
        self.tabs.setObjectName("workspace_tabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(False)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Build the report tab content — parent is tabs so it lives inside the tab widget
        from PySide6.QtWidgets import QTextBrowser  # noqa: PLC0415
        self.report_tab = QWidget()
        report_layout = QVBoxLayout(self.report_tab)
        report_layout.setContentsMargins(0, 0, 0, 0)
        self.report_view = QTextBrowser()
        self.report_view.setObjectName("report_view")
        self.report_view.setOpenExternalLinks(False)
        report_layout.addWidget(self.report_view)

        # primary_canvas is assigned in sync() — never create a floating one here
        self.primary_canvas: DrawingCanvas | None = None
        self._sheets_visible: bool = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def bind_project_state(self, project_state, get_material_fn) -> None:
        self._project_state = project_state
        self._get_material = get_material_fn

    def sync(self) -> None:
        """Rebuild all tabs from current ProjectState."""
        self.tabs.blockSignals(True)
        self.tabs.clear()
        self._plane_tab_canvases = {}

        ps = self._project_state
        if ps.roof_planes:
            if ps.active_roof_plane() is None:
                ps.set_active_plane(ps.roof_planes[0].id)
            for plane in ps.roof_planes:
                tab, canvas = self._build_plane_tab(plane)
                tab_name = plane.name + (" *" if plane.layout_dirty_reason else "")
                self.tabs.addTab(tab, tab_name)
                if plane.id == ps.active_plane_id:
                    self.primary_canvas = canvas
        else:
            placeholder = QWidget(self.tabs)
            layout = QVBoxLayout(placeholder)
            layout.setContentsMargins(0, 0, 0, 0)
            self.primary_canvas = DrawingCanvas(placeholder)
            layout.addWidget(self.primary_canvas)
            self.tabs.addTab(placeholder, "1")

        self.tabs.addTab(self.report_tab, "Raport")
        report_index = self.report_tab_index()
        self.tabs.tabBar().setTabButton(report_index, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.tabs.tabBar().setTabButton(report_index, self.tabs.tabBar().ButtonPosition.LeftSide, None)

        target_index = self._active_plane_tab_index() if ps.roof_planes else 0
        self.tabs.setCurrentIndex(target_index)
        self.tabs.blockSignals(False)

    def report_tab_index(self) -> int:
        return self.tabs.count() - 1

    def plane_id_for_tab_index(self, index: int) -> str | None:
        if index < 0 or index >= self.report_tab_index():
            return None
        widget = self.tabs.widget(index)
        return widget.property("plane_id") if widget is not None else None

    def tab_index_for_plane(self, plane_id: str | None) -> int:
        if plane_id is None:
            return -1
        for index in range(self.report_tab_index()):
            if self.plane_id_for_tab_index(index) == plane_id:
                return index
        return -1

    def update_tab_title(self, plane_id: str, title: str) -> None:
        index = self.tab_index_for_plane(plane_id)
        if index >= 0:
            self.tabs.setTabText(index, title)

    def is_report_tab_index(self, index: int) -> bool:
        return index == self.report_tab_index()

    def toggle_grid(self, enabled: bool) -> None:
        if self.primary_canvas is not None:
            self.primary_canvas.toggle_grid(enabled)
        for canvas in self._plane_tab_canvases.values():
            canvas.toggle_grid(enabled)

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        if self.primary_canvas is not None:
            self.primary_canvas.set_snap_to_grid_enabled(enabled)
        for canvas in self._plane_tab_canvases.values():
            canvas.set_snap_to_grid_enabled(enabled)

    def set_sheet_visibility(self, visible: bool) -> None:
        self._sheets_visible = visible
        if self.primary_canvas is not None:
            self.primary_canvas.set_sheet_visibility(visible)
        for canvas in self._plane_tab_canvases.values():
            canvas.set_sheet_visibility(visible)

    def toggle_module_count(self, enabled: bool) -> None:
        if self.primary_canvas is not None:
            self.primary_canvas.toggle_module_count(enabled)
        for canvas in self._plane_tab_canvases.values():
            canvas.toggle_module_count(enabled)

    def canvas_for_plane(self, plane_id: str) -> DrawingCanvas | None:
        return self._plane_tab_canvases.get(plane_id)

    def plane_canvases(self) -> list[DrawingCanvas]:
        return list(self._plane_tab_canvases.values())

    def update_all_canvases(self) -> None:
        if self.primary_canvas is not None:
            self.primary_canvas.update()
        for canvas in self._plane_tab_canvases.values():
            canvas.update()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_plane_tab(self, plane) -> tuple[QWidget, DrawingCanvas]:
        tab = QWidget(self.tabs)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        canvas = DrawingCanvas(tab)
        canvas.set_roof_plane(plane)
        material = self._get_material(plane.selected_material_id)
        canvas.set_material(material)
        canvas.set_sheet_visibility(self._sheets_visible)
        layout.addWidget(canvas)
        tab.setProperty("plane_id", plane.id)
        self._plane_tab_canvases[plane.id] = canvas
        return tab, canvas

    def _active_plane_tab_index(self) -> int:
        ps = self._project_state
        if ps.active_plane_id is None:
            return 0
        plane_ids = [plane.id for plane in ps.roof_planes]
        try:
            return plane_ids.index(ps.active_plane_id)
        except ValueError:
            return 0
