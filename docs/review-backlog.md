# Review Backlog

This file is the persistent, human-maintained backlog of unresolved PR review guidance for stage work.

Use it together with generated snapshots in `docs/reviews/pr-XXX.md`:
- `docs/reviews/pr-XXX.md` is machine-generated from GitHub exports and should be treated as source material.
- `docs/review-backlog.md` is the canonical triage list that agents should read before starting a new stage.

## Statuses

Allowed statuses:

| Status | Meaning |
| --- | --- |
| `open` | Still relevant and should be considered for the current or next stage. |
| `fixed` | Resolved in code. Leave a short note with the commit, PR, or stage where it was fixed. |
| `deferred` | Reviewed and intentionally postponed to a later stage. |
| `rejected` | Reviewed and intentionally not adopted. |
| `stale` | No longer relevant after later code or workflow changes. |

## Update Rules

- Add or update entries only after checking the generated review snapshot for the relevant PR.
- Keep each backlog item focused on one actionable concern.
- Prefer updating item status instead of deleting old rows so later stages keep the decision history.
- When marking an item `fixed`, `rejected`, `deferred`, or `stale`, add a short note in `Resolution / Notes`.

## Open Items

This table tracks unresolved items that should influence upcoming work.

| Backlog ID | Status | Stage | Source PR | Source Ref | File | Line | Summary | Resolution / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `stage-2-pr4-001` | `open` | `stage-2` | `#4` | `review_comment:3137897199` | `ui/main_window.py` | `459` | Freehand roof-plane creation still converts raw canvas pixels directly into cm coordinates, coupling geometry scale to widget size instead of using `CanvasMapper`. | Still reproducible in `MainWindow._on_polygon_closed()` on `feat/stage6`; important functional bug for drawn geometry and should be fixed before relying on freehand outlines. |
| `stage-2-pr4-002` | `fixed` | `stage-2` | `#4` | `review_comment:3137913119` | `ui/main_window.py` | `555` | Triangle dialog still calls `make_triangle()` outside the normal `_edit`/warning path, so invalid inputs can raise uncaught `ValueError` and leave invalid dialog values in in-memory config. | Fixed in Stage 9 by validating `make_triangle()` before mutating config/state and showing the normal warning flow. |
| `stage-3-pr5-001` | `fixed` | `stage-3` | `#5` | `review_comment:3138030419` | `ui/main_window.py` | `61` | Startup uses `_workspace.sync()` directly, so initial canvases do not get `outline_edit_committed` / `outline_edit_rejected` connections until a later `_refresh_canvas()` call. | Fixed in Stage 9 by switching initial window setup to `_refresh_canvas()`, which wires the first canvas before user edits. |
| `stage-4-pr6-001` | `fixed` | `stage-4` | `#6` | `review_comment:3138202911` | `ui/main_window.py` | `125` | The `Wycinki` menu no longer exposes the existing cutout move workflow, leaving `_dlg_move_hole()` unreachable from the UI. | Fixed in Stage 9 by restoring the move-cutout action in the `Wycinki` menu. |
| `stage-5-pr7-001` | `fixed` | `stage-5` | `#7` | `review_comment:3138630061` | `ui/dialogs/material_dialog.py` | `75` | `BlachyDialog` has only a `Close` button wired to reject, so catalog edits are silently discarded because `MainWindow._dlg_blachy()` only applies changes on `Accepted`. | Fixed in Stage 9 by restoring `Save`/`Cancel` buttons and covering the accept path with a regression test. |
| `stage-5-pr7-002` | `fixed` | `stage-5` | `#7` | `review_comment:3138630280` | `core/models.py` | `163` | `MaterialDefinition.from_dict()` / `to_dict()` still omit the new `min_sheet_length_cm` key from the dual-key migration pattern. | Fixed in Stage 7 while touching `core/models.py` for layout rendering support; both `min_sheet_length_cm` and `min_dlugosc_arkusza` now round-trip. |
| `stage-6-pr8-001` | `open` | `stage-6` | `#8` | `review_comment:3138624666` | `core/layout_engine.py` | `355` | Band piece height is derived from `min(left/right/mid top)` and `max(left/right/mid bottom)`, which can overstate the real strip span on skewed geometry and inflate `raw_length_cm`. | Confirmed against current implementation; this is the most important Stage 6 algorithm issue and should be addressed in the layout engine before further optimization work. |
| `stage-6-pr8-002` | `open` | `stage-6` | `#8` | `review_comment:3138643978` | `tests/test_layout_engine.py` | `33` | The simple-rectangle test contains a tautological `bands` assertion and does not actually validate deterministic band structure. | Still present on `feat/stage6`; test gap is real and should be fixed alongside any Stage 6 algorithm patch. |

## Deferred / Closed Items

Keep non-open items here for traceability.

| Backlog ID | Status | Stage | Source PR | Source Ref | File | Line | Summary | Resolution / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `stage-2-pr3-001` | `fixed` | `stage-2` | `#3` | `review_comment:3137012060` | `ui/main_window.py` | `393` | Starting draw mode creates and persists an empty plane before the user confirms the freehand polygon, which leaves a stray saved tab when drawing is cancelled. | Fixed in the stage-2 dialog geometry patch by delaying plane creation until geometry is actually confirmed. |
| `stage-2-pr3-002` | `fixed` | `stage-2` | `#3` | `review_comment:3137018786` | `ui/main_window.py` | `396` | Re-entering draw mode can accumulate `polygon_closed` signal connections and create duplicate planes when the polygon is finally closed. | Fixed in the stage-2 dialog geometry patch by disconnecting any previous `polygon_closed` handler before reconnecting draw mode. |
| `stage-2-pr3-003` | `fixed` | `stage-2` | `#3` | `review_comment:3137018682` | `core/project_state.py` | `289` | `move_hole_in_plane` is missing the new `plane.outline is None` guard, so geometry validation can crash on empty planes. | Fixed in the stage-2 dialog geometry patch via the shared `_require_plane_outline()` guard. |
| `stage-2-pr3-004` | `fixed` | `stage-2` | `#3` | `review_comment:3137009525` | `ui/main_window.py` | `57` | Remove the redundant early assignment of `self._workspace.primary_canvas` before `self._workspace.sync()` populates it. | Fixed in the stage-2 dialog geometry patch by removing the redundant pre-sync assignment. |
| `stage-2-pr3-005` | `fixed` | `stage-2` | `#3` | `review_comment:3137009522` | `core/project_state.py` | `206` | Consider extracting repeated active-plane and outline validation into a helper to reduce duplicated guards. | Fixed in the stage-2 dialog geometry patch by introducing `_require_plane()` and `_require_plane_outline()`. |
| `stage-2-pr4-003` | `rejected` | `stage-2` | `#4` | `review_comment:3137897208` | `ui/main_window.py` | `393` | Replace manual signal disconnect logic with `Qt.UniqueConnection` for polygon close handling. | Not promoted to an open backlog item: current code already prevents duplicate handlers explicitly; this is an idiomatic cleanup, not a current correctness issue. |
| `stage-2-pr4-004` | `deferred` | `stage-2` | `#4` | `review_comment:3137897223` | `core/geometry.py` | `43` | `make_triangle()` rejects some geometrically valid obtuse/right configurations when `horizontal >= base_cm`. | Business rule is still ambiguous: the app may intentionally constrain the apex to remain above the base span. Revisit when triangle shape semantics are clarified. |
| `stage-3-pr5-002` | `deferred` | `stage-3` | `#5` | `review_comment:3138031860` | `ui/main_window.py` | `197` | Move signal connection management out of `_refresh_canvas()` and closer to canvas lifecycle. | Valid cleanup direction, but lower priority than the missing startup wiring bug and not urgent for current stage work. |
| `stage-3-pr5-003` | `deferred` | `stage-3` | `#5` | `review_comment:3138031865` | `ui/drawing_canvas.py` | `554` | Avoid calling `validate_polygon()` from `paintEvent()` during drag previews. | Performance-oriented suggestion; current polygons are small and the bug severity is lower than the functional regressions above. |
| `stage-4-pr6-002` | `rejected` | `stage-4` | `#6` | `review_comment:3138210205` | `ui/drawing_canvas.py` | `266` | Remove the standalone `validate_polygon()` call before `validate_hole_polygon()`. | Not promoted: the duplicate validation is mildly redundant but harmless, and the separate branch still covers the no-outline case cleanly. |
| `stage-4-pr6-003` | `rejected` | `stage-4` | `#6` | `review_comment:3138210242` | `ui/main_window.py` | `496` | Remove the `len(pixel_points) < 3` guard in `_on_cutout_closed()` because the canvas already enforces it. | Keeping the guard is acceptable defensive programming in the slot; no action needed. |
| `stage-5-pr7-003` | `deferred` | `stage-5` | `#7` | `review_comment:3138608981` | `core/project_state.py` | `127` | Use dataclass equality/replacement instead of `to_dict()` comparison and field-by-field copying in `upsert_material()`. | Maintainability improvement only; current behavior is correct, so this stays out of the active backlog. |
| `stage-5-pr7-004` | `deferred` | `stage-5` | `#7` | `review_comment:3138609012` | `core/project_state.py` | `148` | Simplify `replace_materials()` to avoid repeated linear `material_by_id()` searches. | Efficiency cleanup with limited impact at current dataset sizes; defer unless material catalog size grows or the method is being refactored anyway. |
| `stage-6-pr8-003` | `deferred` | `stage-6` | `#8` | `review_comment:3138614397` | `core/layout_engine.py` | `112` | Move `_UnionFind` into a shared utility module. | Modularity suggestion only; no immediate correctness issue. |
| `stage-6-pr8-004` | `deferred` | `stage-6` | `#8` | `review_comment:3138614404` | `core/layout_engine.py` | `396` | Move `_unique_sorted()` into shared geometry/utility code. | Utility extraction is optional and can wait until there is a second real caller. |

## Review Sources

Record generated review snapshots here so future agents can find them quickly.

| PR | Snapshot | Notes |
| --- | --- | --- |
| `#3` | `docs/reviews/pr-003.md` | Create or refresh with `scripts/export-pr-review.sh` and `scripts/sync-review-backlog.py`. |
| `#4` | `docs/reviews/pr-004.md` | Triaged on `feat/stage6`; contains two still-open UI geometry issues and several lower-priority follow-ups. |
| `#5` | `docs/reviews/pr-005.md` | Triaged on `feat/stage6`; startup signal wiring remains relevant, while the rest is performance/cleanup work. |
| `#6` | `docs/reviews/pr-006.md` | Triaged on `feat/stage6`; cutout move menu regression remains open. |
| `#7` | `docs/reviews/pr-007.md` | Triaged on `feat/stage6`; material dialog accept path and material key migration are still open. |
| `#8` | `docs/reviews/pr-008.md` | Triaged on `feat/stage6`; layout engine slab-span issue and missing test assertion remain open. |
