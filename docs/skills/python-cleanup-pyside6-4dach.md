# SKILL: 4dach PySide6 Python Cleanup Protocol

This skill adapts the universal Python cleanup protocol to the `4dach` PySide6 desktop application.

Use this file when cleaning this repository or a closely related PySide6/Qt desktop project. For general Python repositories, start with `docs/skills/python-cleanup-universal.md` instead.

---

## 1. Project-specific hard rules

This repository has stricter workflow requirements than a generic Python repo.

- Python version: **3.11**.
- Environment manager: **uv**.
- Default test command: `uv run pytest`.
- Do not use plain `pip install`; use `uv add` or `uv add --dev`.
- Do not work directly on `main` or `master`.
- Preserve the current branch structure and stacked PR workflow.
- Read `AGENTS.md` before implementation.
- Read `docs/review-backlog.md` before implementation if it exists.
- Do not mix Qt/UI logic into pure domain logic under `core/`.
- Do not silently change persistence formats.
- Do not run broad auto-fix tools while the working tree has conflicts or unrelated user changes.

Current safe command style:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run vulture .
uv run deptry .
```

---

## 2. Mandatory pre-flight check

Before any cleanup work, run read-only checks:

```bash
git status --short
git branch --show-current
git log --oneline -5
git stash list --date=local
```

Then inspect project instructions:

```bash
cat AGENTS.md
cat docs/review-backlog.md
```

If `git status` contains conflicts such as `UU file.py`, stop. Do not run `ruff --fix`, formatters, or dependency cleanup until the conflict is resolved by the owner or by a task explicitly dedicated to that conflict.

If a stash exists, report it. Do not drop it. Do not assume it is yours.

---

## 3. Recommended branch split for this repo

Use focused branches/commits:

```bash
git checkout -b chore/python-cleanup-skills
git checkout -b chore/python-quality-tooling
git checkout -b refactor/ruff-import-cleanup
git checkout -b refactor/vulture-dead-code-review
git checkout -b chore/deptry-dependency-cleanup
```

Recommended split:

1. `docs/skills/*` only.
2. Tooling config only (`pyproject.toml`, pre-commit, CI).
3. Ruff auto-fix only.
4. Manual dead-code cleanup only.
5. Dependency cleanup only.

Do not combine docs/tooling setup with broad code auto-fixes.

---

## 4. PySide6 / Qt false-positive hazards

### Signal/slot methods

Vulture may mark methods as unused even when they are connected dynamically:

```python
button.clicked.connect(self.on_button_clicked)
canvas.polygon_closed.connect(self._on_polygon_closed)
```

Before deleting any method in a class inheriting from `QObject`, `QWidget`, `QMainWindow`, `QDialog`, or any Qt widget:

```bash
rg "method_name|connect\(|Signal\(|Slot\(" .
rg "method_name" . --glob '*.ui'
```

If a method is used by a signal, `.ui` file, action callback, or dynamic lookup, do not delete it. Prefer Vulture whitelist.

### `.ui` files and generated files

This project has:

- `form.ui`
- `ui_form.py`

`ui_form.py` is generated code. Do not manually refactor it during cleanup. Exclude it from Ruff/Vulture unless the project explicitly decides otherwise.

### Qt resource imports

Never blindly remove imports ending in `_rc` or modules that register Qt resources/plugins. If Ruff flags them as unused, preserve them with:

```python
import resources_rc  # noqa: F401
```

### App icons and static resource modules

`app_icons.py` contains static SVG/icon data and Qt icon construction. Treat it as resource-like code. Do not run aggressive simplification or dead-code deletion there unless a focused test/visual review exists.

---

## 5. Suggested tooling configuration for this repo

Do not apply this while the working tree has conflicts. Add it in a dedicated tooling branch.

### Dependencies

```bash
uv add --dev ruff vulture deptry
```

### `pyproject.toml` conservative baseline

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
exclude = [
    "ui_form.py",
    "*_rc.py",
    "app_icons.py",
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
]

[tool.ruff.lint]
select = ["F", "I"]
fixable = ["F", "I"]

[tool.ruff.lint.isort]
known-first-party = ["core", "ui"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.vulture]
paths = ["."]
exclude = ["ui_form.py", "tests/", ".venv/", "build/", "dist/"]
min_confidence = 80

[tool.deptry]
exclude = [".venv", "build", "dist", ".codex"]

[tool.deptry.per_rule_ignores]
DEP002 = ["pytest-qt", "ruff", "vulture", "deptry"]
```

After baseline is clean, consider expanding Ruff gradually:

```toml
[tool.ruff.lint]
select = ["F", "E", "W", "I", "UP", "B", "C4"]
ignore = ["E501"]
fixable = ["F", "I", "UP", "B", "C4"]
```

Do not add `SIM` broadly until tests and GUI behavior are stable.

---

## 6. Pre-commit policy for this repo

Start with Ruff only:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Add deptry only once `uv run deptry .` is clean.

Prefer Vulture manual stage:

```yaml
  - repo: https://github.com/jendrikseipp/vulture
    rev: v2.16
    hooks:
      - id: vulture
        stages: [manual]
```

Rationale: PySide6 signal/slot code produces false positives and should not block every commit until whitelisted.

---

## 7. CI policy for this repo

Do not introduce blocking CI for checks that currently fail.

A safe first workflow should be aligned with `uv`:

```yaml
name: Python Quality
on:
  pull_request:
  workflow_dispatch:

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Sync dependencies
        run: uv sync
      - name: Ruff
        run: uv run ruff check . && uv run ruff format --check .
      - name: Tests
        run: uv run pytest
```

If `deptry` or `vulture` is not clean yet, run them as explicit reports first:

```yaml
      - name: deptry report
        run: uv run deptry . || true
      - name: Vulture report
        run: uv run vulture . || true
```

Convert them to blocking only after triage.

---

## 8. Safe Ruff workflow for this repo

### Baseline

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

### Fix only low-risk import issues

```bash
uv run ruff check . --select F,I --fix
uv run ruff format .
uv run pytest
```

Review diff carefully:

```bash
git diff --stat
git diff -- ui/ core/ tests/
```

If tests fail, do not commit broad auto-fixes. Revert or split the diff.

---

## 9. Safe Vulture workflow for this repo

```bash
uv run vulture .
uv run vulture . --min-confidence 90
```

For each finding:

1. Search text references with `rg`.
2. Search `.ui` files.
3. Search signal/slot connections.
4. Check actions, menus, toolbar callbacks, and dialog methods.
5. Prefer whitelist over deletion when uncertain.

Example whitelist generation:

```bash
uv run vulture . --make-whitelist > whitelist.py
```

Only commit `whitelist.py` if the team accepts it as a maintained artifact.

---

## 10. Safe deptry workflow for this repo

```bash
uv run deptry .
```

Before removing a dependency, check:

- runtime imports in `core/`, `ui/`, root modules
- tests and pytest plugins
- generated Qt code
- packaging/build workflows
- GitHub Actions
- image snapshot tests

Use per-rule ignores for known dev-only or dynamically used packages.

---

## 11. GUI smoke test expectations

After any cleanup touching GUI files (`ui/`, `dialogs.py`, `mainwindow.py`, `app_icons.py`, `ui_form.py`):

```bash
uv run pytest
```

If possible, also launch the app manually or through an agreed smoke-test command:

```bash
uv run python3 __main__.py
```

Watch for:

- `AttributeError` on missing slot methods
- missing icons/resources
- broken menu/toolbar actions
- broken dialogs
- coordinate/grid regressions in canvas behavior

If manual GUI validation is not performed, state that clearly in the final report.

---

## 12. Required final report for this repo

Final response must include:

- Branch name.
- Files changed.
- Whether `AGENTS.md` and `docs/review-backlog.md` were checked.
- Whether any review-backlog items were touched or left unchanged.
- Exact commands run.
- Test results, especially `uv run pytest`.
- Remaining Ruff/Vulture/deptry issues.
- Whether any stash existed, was created, or was left untouched.
- Whether GUI smoke testing was done.
- Whether PR/stack actions were actually performed.

---

## 13. 4dach cleanup checklist

- [ ] Read `AGENTS.md`.
- [ ] Read `docs/review-backlog.md`.
- [ ] Checked `git status --short`.
- [ ] Confirmed no unresolved conflict before auto-fix.
- [ ] Checked `git stash list` and reported existing stash entries.
- [ ] Used `uv run` for tools.
- [ ] Did not touch generated Qt files unless explicitly intended.
- [ ] Checked `.ui`, signal/slot, action, and callback references before deleting GUI code.
- [ ] Ran `uv run pytest` after changes.
- [ ] Documented GUI smoke test status.
- [ ] Kept commits small and stage-focused.
