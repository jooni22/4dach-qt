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
| `stage-2-pr4-002` | `fixed` | `stage-2` | `#4` | `review_comment:3137913119` | `ui/main_window.py` | `555` | Triangle dialog still calls `make_triangle()` outside the normal `_edit`/warning path, so invalid inputs can raise uncaught `ValueError` and leave invalid dialog values in in-memory config. | Fixed in Stage 9 by validating `make_triangle()` before mutating config/state and showing the normal warning flow. |
| `stage-3-pr5-001` | `fixed` | `stage-3` | `#5` | `review_comment:3138030419` | `ui/main_window.py` | `61` | Startup uses `_workspace.sync()` directly, so initial canvases do not get `outline_edit_committed` / `outline_edit_rejected` connections until a later `_refresh_canvas()` call. | Fixed in Stage 9 by switching initial window setup to `_refresh_canvas()`, which wires the first canvas before user edits. |
| `stage-4-pr6-001` | `fixed` | `stage-4` | `#6` | `review_comment:3138202911` | `ui/main_window.py` | `125` | The `Wycinki` menu no longer exposes the existing cutout move workflow, leaving `_dlg_move_hole()` unreachable from the UI. | Fixed in Stage 9 by restoring the move-cutout action in the `Wycinki` menu. |
| `stage-5-pr7-001` | `fixed` | `stage-5` | `#7` | `review_comment:3138630061` | `ui/dialogs/material_dialog.py` | `75` | `BlachyDialog` has only a `Close` button wired to reject, so catalog edits are silently discarded because `MainWindow._dlg_blachy()` only applies changes on `Accepted`. | Fixed in Stage 9 by restoring `Save`/`Cancel` buttons and covering the accept path with a regression test. |
| `stage-5-pr7-002` | `fixed` | `stage-5` | `#7` | `review_comment:3138630280` | `core/models.py` | `163` | `MaterialDefinition.from_dict()` / `to_dict()` still omit the new `min_sheet_length_cm` key from the dual-key migration pattern. | Fixed in Stage 7 while touching `core/models.py` for layout rendering support; both `min_sheet_length_cm` and `min_dlugosc_arkusza` now round-trip. |

## Deferred / Closed Items

Keep non-open items here for traceability.

| Backlog ID | Status | Stage | Source PR | Source Ref | File | Line | Summary | Resolution / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `stage-2-pr3-001` | `fixed` | `stage-2` | `#3` | `review_comment:3137012060` | `ui/main_window.py` | `393` | Starting draw mode creates and persists an empty plane before the user confirms the freehand polygon, which leaves a stray saved tab when drawing is cancelled. | Fixed in the stage-2 dialog geometry patch by delaying plane creation until geometry is actually confirmed. |
| `stage-2-pr3-002` | `fixed` | `stage-2` | `#3` | `review_comment:3137018786` | `ui/main_window.py` | `396` | Re-entering draw mode can accumulate `polygon_closed` signal connections and create duplicate planes when the polygon is finally closed. | Fixed in the stage-2 dialog geometry patch by disconnecting any previous `polygon_closed` handler before reconnecting draw mode. |
| `stage-2-pr3-003` | `fixed` | `stage-2` | `#3` | `review_comment:3137018682` | `core/project_state.py` | `289` | `move_hole_in_plane` is missing the new `plane.outline is None` guard, so geometry validation can crash on empty planes. | Fixed in the stage-2 dialog geometry patch via the shared `_require_plane_outline()` guard. |
| `stage-2-pr3-004` | `fixed` | `stage-2` | `#3` | `review_comment:3137009525` | `ui/main_window.py` | `57` | Remove the redundant early assignment of `self._workspace.primary_canvas` before `self._workspace.sync()` populates it. | Fixed in the stage-2 dialog geometry patch by removing the redundant pre-sync assignment. |
| `stage-2-pr3-005` | `fixed` | `stage-2` | `#3` | `review_comment:3137009522` | `core/project_state.py` | `206` | Consider extracting repeated active-plane and outline validation into a helper to reduce duplicated guards. | Fixed in the stage-2 dialog geometry patch by introducing `_require_plane()` and `_require_plane_outline()`. |
| `stage-2-pr4-001` | `fixed` | `stage-2` | `#4` | `review_comment:3137897199` | `ui/main_window.py` | `459` | Freehand roof-plane creation still converts raw canvas pixels directly into cm coordinates, coupling geometry scale to widget size instead of using `CanvasMapper`. | Fixed on `fix-after-9stage` by normalizing freehand polygons through `CanvasMapper` into a stable 1000x1000 domain and covering it with a widget-size regression test. |
| `stage-2-pr4-003` | `rejected` | `stage-2` | `#4` | `review_comment:3137897208` | `ui/main_window.py` | `393` | Replace manual signal disconnect logic with `Qt.UniqueConnection` for polygon close handling. | Not promoted to an open backlog item: current code already prevents duplicate handlers explicitly; this is an idiomatic cleanup, not a current correctness issue. |
| `stage-2-pr4-004` | `deferred` | `stage-2` | `#4` | `review_comment:3137897223` | `core/geometry.py` | `43` | `make_triangle()` rejects some geometrically valid obtuse/right configurations when `horizontal >= base_cm`. | Business rule is still ambiguous: the app may intentionally constrain the apex to remain above the base span. Revisit when triangle shape semantics are clarified. |
| `stage-3-pr5-002` | `deferred` | `stage-3` | `#5` | `review_comment:3138031860` | `ui/main_window.py` | `197` | Move signal connection management out of `_refresh_canvas()` and closer to canvas lifecycle. | Valid cleanup direction, but lower priority than the missing startup wiring bug and not urgent for current stage work. |
| `stage-3-pr5-003` | `deferred` | `stage-3` | `#5` | `review_comment:3138031865` | `ui/drawing_canvas.py` | `554` | Avoid calling `validate_polygon()` from `paintEvent()` during drag previews. | Performance-oriented suggestion; current polygons are small and the bug severity is lower than the functional regressions above. |
| `stage-4-pr6-002` | `rejected` | `stage-4` | `#6` | `review_comment:3138210205` | `ui/drawing_canvas.py` | `266` | Remove the standalone `validate_polygon()` call before `validate_hole_polygon()`. | Not promoted: the duplicate validation is mildly redundant but harmless, and the separate branch still covers the no-outline case cleanly. |
| `stage-4-pr6-003` | `rejected` | `stage-4` | `#6` | `review_comment:3138210242` | `ui/main_window.py` | `496` | Remove the `len(pixel_points) < 3` guard in `_on_cutout_closed()` because the canvas already enforces it. | Keeping the guard is acceptable defensive programming in the slot; no action needed. |
| `stage-5-pr7-003` | `deferred` | `stage-5` | `#7` | `review_comment:3138608981` | `core/project_state.py` | `127` | Use dataclass equality/replacement instead of `to_dict()` comparison and field-by-field copying in `upsert_material()`. | Maintainability improvement only; current behavior is correct, so this stays out of the active backlog. |
| `stage-5-pr7-004` | `deferred` | `stage-5` | `#7` | `review_comment:3138609012` | `core/project_state.py` | `148` | Simplify `replace_materials()` to avoid repeated linear `material_by_id()` searches. | Efficiency cleanup with limited impact at current dataset sizes; defer unless material catalog size grows or the method is being refactored anyway. |
| `stage-6-pr8-001` | `fixed` | `stage-6` | `#8` | `review_comment:3138624666` | `core/layout_engine.py` | `355` | Band piece height is derived from `min(left/right/mid top)` and `max(left/right/mid bottom)`, which can overstate the real strip span on skewed geometry and inflate `raw_length_cm`. | Fixed on `fix-render` by using the full envelope of all sampled cross-sections (min top / max bottom). This intentionally covers the complete slanted edge, eliminating visible gaps. Oversized sheets are handled by the new transverse split logic. |
| `stage-6-pr8-002` | `fixed` | `stage-6` | `#8` | `review_comment:3138643978` | `tests/test_layout_engine.py` | `33` | The simple-rectangle test contains a tautological `bands` assertion and does not actually validate deterministic band structure. | Fixed on `fix-render` by asserting explicit band structure and adding envelope and transverse-split regression tests. |
| `stage-6-pr8-003` | `deferred` | `stage-6` | `#8` | `review_comment:3138614397` | `core/layout_engine.py` | `112` | Move `_UnionFind` into a shared utility module. | Modularity suggestion only; no immediate correctness issue. |
| `stage-6-pr8-004` | `deferred` | `stage-6` | `#8` | `review_comment:3138614404` | `core/layout_engine.py` | `396` | Move `_unique_sorted()` into shared geometry/utility code. | Utility extraction is optional and can wait until there is a second real caller. |
| `stage-7-pr9-001` | `deferred` | `stage-7` | `#9` | `review_comment:3139036653` | `ui/drawing_canvas.py` | `265` | Sheet hit-testing still uses rectangle/order-based checks, so overlapping or cutout-shaped placements can select a sheet that is visually behind or absent in the clicked hole area. | Real UX inconsistency from PR #9 triage, but lower priority than the functional geometry/reporting bugs fixed in this stage. |
| `stage-8-pr10-001` | `fixed` | `stage-8` | `#10` | `review_comment:3139052756` | `core/reporting.py` | `227` | `build_report_html()` rebuilds the plane section from persisted `ProjectState` placements instead of the supplied `report`, so HTML can disagree with the provided layout result. | Fixed on `fix-after-9stage` by keeping preview geometry from state but overriding section totals, BOM rows, and warnings from the supplied `LayoutReport`. |
| `stage-9-pr11-001` | `fixed` | `stage-9` | `#11` | `review_comment:3139668545` | `ui/main_window.py` | `309` | `_open_project()` does not reset cached report HTML / plane id or refresh the company title, leaving stale report content and window title after loading another project. | Fixed on `fix-after-9stage` by mirroring `_apply_snapshot()` resets in `_open_project()` and covering the reload path with a UI regression test. |

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
| `#9` | `docs/reviews/pr-009.md` | Triaged on `fix-after-9stage`; one hit-test UX inconsistency stays deferred, while caching/order suggestions remain out of scope. |
| `#10` | `docs/reviews/pr-010.md` | Triaged on `fix-after-9stage`; HTML/report inconsistency was fixed, while reporting side effects and DRY cleanup remain deferred. |
| `#11` | `docs/reviews/pr-011.md` | Triaged on `fix-after-9stage`; stale report/title reset bug in `_open_project()` was fixed. |
