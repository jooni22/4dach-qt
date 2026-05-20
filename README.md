# 4Dach

4Dach is a PySide6 desktop application for defining roof planes, adding cutouts,
laying out roofing sheets, and generating a project report for metal roofing
work.

## Stack

- Python 3.11+
- PySide6
- uv
- pytest + pytest-qt

## Structure

- `__main__.py`, `mainwindow.py`, `form.ui`, `app_icons.py` - app entrypoints and UI assets
- `core/` - domain models, geometry, layout, project state, reporting, and canvas mapping
- `ui/` - Qt widgets, dialogs, toolbar, theme, workspace, and canvas code
- `tests/` - logic and Qt contract tests
- `project_files.py` - canonical project container filenames and slug handling

The local `docs/` directory is ignored scratch/reference material. It is not the
source of truth for current behavior unless a user explicitly points to a file in
that directory.

## Development

Install dependencies:

```bash
uv sync
```

Run the app:

```bash
uv run python __main__.py
```

Run tests:

```bash
uv run pytest
```

Run focused checks:

```bash
uv run pytest tests/test_mainwindow_ui_contract.py -q
uv run pytest tests/test_drawing_canvas.py -q
uv run ruff check path/to/touched_file.py
```

## Project Files

Projects are stored as a directory plus generated artifacts:

```text
<projects_dir>/<slug>/
├── project.4dach
└── report.html
```

`project.4dach` is the application project payload. `report.html` is the last
generated browser report for that project.
