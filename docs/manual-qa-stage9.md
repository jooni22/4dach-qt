# Stage 9 Manual QA

## Multi-tab Editing

1. Open a project with at least two roof planes.
2. Change geometry on the first tab and rename the second tab.
3. Verify the window title gains `*` and only changed tabs gain the unsaved marker.
4. Use `Ctrl+Z` / `Ctrl+Shift+Z` across tabs and confirm the active project state updates predictably.
5. Close the window and verify the Save / Discard / Cancel flow appears.

## Repeated Vertex Dragging

1. Open an existing roof plane with an outline.
2. Drag the same outline vertex repeatedly in short movements.
3. Confirm the canvas stays responsive, invalid drags are rejected, and the plane remains selected.
4. Use undo/redo after several drags and verify the outline returns to earlier states in order.

## Cutout Editing

1. Add a cutout from the menu and a second cutout from draw mode.
2. Move a cutout from `Wycinki -> Przesuń wycinek...`.
3. Drag a cutout vertex inside the plane, then try an invalid drag outside the outline.
4. Confirm valid edits persist, invalid edits warn without corrupting geometry, and undo/redo works for add/edit/remove.

## Material Changes

1. Change the active plane material from the toolbar combo.
2. Edit the material catalog in `Katalog -> Blachy...` and save the dialog.
3. Confirm only roof planes using the edited material become layout-dirty.
4. Undo and redo the material change and verify canvas labels and dirty markers follow the restored state.

## Report Generation After Many Edits

1. Make several geometry, cutout, and material edits across multiple tabs without saving.
2. Generate the report.
3. When prompted, choose recalculation and verify only dirty planes are recomputed.
4. Confirm the report opens successfully and the project still shows unsaved changes until an explicit save.

## Save / Reload

1. Save the edited project with `Ctrl+S`.
2. Confirm dirty markers disappear.
3. Reopen the project with `Ctrl+O`.
4. Verify geometry, cutouts, materials, and layout state round-trip correctly.
