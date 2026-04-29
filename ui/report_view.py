"""report_view.py — ReportController manages the HTML report tab."""
from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser


class ReportController:
    """Owns the QTextBrowser and knows how to render report states."""

    def __init__(self, report_view: QTextBrowser) -> None:
        self._view = report_view

    def show_html(self, html: str) -> None:
        self._view.setHtml(html)

    def show_placeholder(self, active_plane, dirty_reason_label_fn, dirty_reason_hint_fn) -> None:
        """Render the appropriate placeholder when no report has been generated."""
        if active_plane is None:
            content = (
                "<html><body>"
                "<h1>Raport 4Dach</h1>"
                "<p>Dodaj połać, aby wygenerować pierwszy raport.</p>"
                "</body></html>"
            )
        else:
            dirty_msg = ""
            if active_plane.layout_dirty_reason:
                reason_label = dirty_reason_label_fn(active_plane.layout_dirty_reason)
                reason_hint = dirty_reason_hint_fn(active_plane.layout_dirty_reason)
                dirty_msg = (
                    f"<p><strong>Stan layoutu:</strong> {reason_label}.</p>"
                    f"<p>{reason_hint}</p>"
                )
            content = (
                "<html><body>"
                f"<h1>Raport 4Dach - {active_plane.name}</h1>"
                "<p>Raport nie został jeszcze wygenerowany dla aktywnej połaci.</p>"
                f"{dirty_msg}"
                "<p>Użyj akcji <strong>Plik → Drukuj raport</strong> lub "
                "<strong>Arkusze → Przelicz aktywną połać</strong>, aby przeliczyć layout.</p>"
                "</body></html>"
            )
        self._view.setHtml(content)

    def set_cached_or_placeholder(
        self,
        active_plane,
        cached_html: str,
        cached_plane_id: str | None,
        dirty_reason_label_fn,
        dirty_reason_hint_fn,
    ) -> None:
        if (
            cached_html
            and (
                cached_plane_id is None
                or (active_plane is not None and cached_plane_id == active_plane.id)
            )
        ):
            self._view.setHtml(cached_html)
        else:
            self.show_placeholder(active_plane, dirty_reason_label_fn, dirty_reason_hint_fn)
