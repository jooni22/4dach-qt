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
| _none currently_ | - | - | - | - | - | - | No unresolved stage backlog items remain after the current stage-2 geometry work. | Re-open this table when new review items are triaged. |

## Deferred / Closed Items

Keep non-open items here for traceability.

| Backlog ID | Status | Stage | Source PR | Source Ref | File | Line | Summary | Resolution / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `stage-2-pr3-001` | `fixed` | `stage-2` | `#3` | `review_comment:3137012060` | `ui/main_window.py` | `393` | Starting draw mode creates and persists an empty plane before the user confirms the freehand polygon, which leaves a stray saved tab when drawing is cancelled. | Fixed in the stage-2 dialog geometry patch by delaying plane creation until geometry is actually confirmed. |
| `stage-2-pr3-002` | `fixed` | `stage-2` | `#3` | `review_comment:3137018786` | `ui/main_window.py` | `396` | Re-entering draw mode can accumulate `polygon_closed` signal connections and create duplicate planes when the polygon is finally closed. | Fixed in the stage-2 dialog geometry patch by disconnecting any previous `polygon_closed` handler before reconnecting draw mode. |
| `stage-2-pr3-003` | `fixed` | `stage-2` | `#3` | `review_comment:3137018682` | `core/project_state.py` | `289` | `move_hole_in_plane` is missing the new `plane.outline is None` guard, so geometry validation can crash on empty planes. | Fixed in the stage-2 dialog geometry patch via the shared `_require_plane_outline()` guard. |
| `stage-2-pr3-004` | `fixed` | `stage-2` | `#3` | `review_comment:3137009525` | `ui/main_window.py` | `57` | Remove the redundant early assignment of `self._workspace.primary_canvas` before `self._workspace.sync()` populates it. | Fixed in the stage-2 dialog geometry patch by removing the redundant pre-sync assignment. |
| `stage-2-pr3-005` | `fixed` | `stage-2` | `#3` | `review_comment:3137009522` | `core/project_state.py` | `206` | Consider extracting repeated active-plane and outline validation into a helper to reduce duplicated guards. | Fixed in the stage-2 dialog geometry patch by introducing `_require_plane()` and `_require_plane_outline()`. |

## Review Sources

Record generated review snapshots here so future agents can find them quickly.

| PR | Snapshot | Notes |
| --- | --- | --- |
| `#3` | `docs/reviews/pr-003.md` | Create or refresh with `scripts/export-pr-review.sh` and `scripts/sync-review-backlog.py`. |
