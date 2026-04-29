# Test plan: canvas grid snapping refactor

## What changed in user-visible terms

Grid drawing and snapping were consolidated so the canvas uses one grid context per interaction mode. In practice, drawing a freehand outline should now show the same full-canvas grid and snap to the same points even when an existing roof outline and a custom zero point already exist.

## Setup/access status

- Environment: local PySide6 desktop app.
- Launch command: `uv run python3 __main__.py`.
- Credentials: no external login, API token, or saved secret is required for this test.
- Available environment config already documents `uv sync`, `uv run python3 __main__.py`, and `uv run pytest -q`.

## Code paths traced

- `ui/main_window.py:147-151` exposes `Kształt > Dowolny`, which starts freehand outline capture.
- `ui/main_window.py:922-945` switches the primary canvas into `MODE_DRAW_OUTLINE`.
- `ui/toolbar.py:151-166` exposes the `Snap to Grid` toolbar action.
- `ui/toolbar.py:93-94` and `ui/main_window.py:863-875` expose `Ustaw punkt zerowy` for custom origin editing.
- `ui/drawing_canvas.py:352-374` now selects the free-draw mapper/origin in `MODE_DRAW_OUTLINE`.
- `ui/drawing_canvas.py:1100-1109` now uses free-draw bounds for the grid in `MODE_DRAW_OUTLINE`, even if an existing outline is present.
- `ui/drawing_canvas.py:1128-1141` snaps clicked draw points through `_pixel_to_domain_point()` before storing them.
- `ui/main_window.py:970-977` closes a freehand polygon by unmapping the stored snapped pixels, without applying a second snap.

## Primary flow

Run one recorded GUI flow against a deterministic project state:

1. Start the desktop app with an existing rectangular roof plane visible and `Snap to Grid` checked.
2. Enable `Ustaw punkt zerowy`, drag the zero point away from the rectangle's default top-left corner, and disable zero-point edit mode.
3. Open `Kształt > Dowolny`.
4. Verify draw-outline mode appears over the existing roof plane.
5. Click three intentionally off-grid canvas locations that correspond to free-draw domain points near `(270, 43)`, `(320, 43)`, and `(350, 100)`, then close the polygon.
6. Inspect the resulting active outline coordinates from the running app state.

Execution note: after actions that refresh the workspace (especially committing the dragged zero point), the test harness must reacquire the current active canvas before continuing. This does not change the user-visible flow; it only prevents the harness from clicking an old widget instance.

## Key assertions

- **Passed only if** draw-outline mode shows grid lines spanning the full canvas width and height, not just the small existing rectangle bounds. A broken mapper/bounds implementation would show the grid clipped to the existing outline area.
- **Passed only if** the first off-grid click near domain `(270, 43)` is stored as approximately `(275.0, 50.0)` after the polygon is closed. A broken close-time double-snap with a custom zero point would shift this coordinate to a different grid line.
- **Passed only if** all three closed outline vertices are snapped to the 25 cm free-draw grid: approximately `(275, 50)`, `(325, 50)`, and `(350, 100)`.
- **Passed only if** after closing the polygon the new outline replaces the previous rectangle and remains visible in normal view mode, confirming the full MainWindow/canvas signal path completed.

## Evidence to capture

- Screen recording of the GUI interaction, with annotations for draw mode, full-canvas grid, polygon close, and coordinate verification.
- Screenshot or console evidence from the running app state showing the final outline vertices.
