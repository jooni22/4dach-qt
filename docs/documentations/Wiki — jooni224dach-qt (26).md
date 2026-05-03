## Code Quality & Review Workflow

Relevant source files

-   [.github/workflows/lint.yml](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml)
-   [.pre-commit-config.yaml](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml)
-   [AGENTS.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1)
-   [\_TODO.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/_TODO.md?plain=1)
-   [docs/SKILL.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1)
-   [docs/knowledge/rysowanie-figury-dekarstwo.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/knowledge/rysowanie-figury-dekarstwo.md?plain=1)
-   [docs/review-backlog.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/review-backlog.md?plain=1)
-   [docs/skills/python-cleanup-pyside6-4dach.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-pyside6-4dach.md?plain=1)
-   [docs/skills/python-cleanup-universal.md](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-universal.md?plain=1)
-   [pyproject.toml](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml)
-   [scripts/cleanup\_preview.sh](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/cleanup_preview.sh)
-   [scripts/export-pr-review.sh](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/export-pr-review.sh)
-   [scripts/sync-review-backlog.py](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/sync-review-backlog.py)

This page documents the technical standards, automated tooling, and human-in-the-loop review processes that ensure the stability and maintainability of the 4Dach codebase. The workflow is designed to handle the specific challenges of a PySide6 desktop application, such as dynamic signal/slot connections and binary resource management.

## Automated Quality Tooling

The project utilizes a multi-layered linting and static analysis suite managed via `uv`. These tools are configured in `pyproject.toml` and enforced through both local pre-commit hooks and GitHub Actions.

### Ruff: Linting and Formatting

Ruff serves as the primary engine for linting, import sorting (`isort`), and code formatting. It is configured to target Python 3.11 [pyproject.toml#40](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L40-L40)

-   Ruleset: The configuration selects several rule categories including Pyflakes (`F`), pycodestyle (`E`, `W`), isort (`I`), pyupgrade (`UP`), and flake8-bugbear (`B`) [pyproject.toml#53-62](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L53-L62)
-   Fixable Rules: Many violations are automatically resolved using `ruff check . --fix`, specifically for imports, upgrades, and common simplifications [pyproject.toml#64](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L64-L64)
-   Import Sorting: The `known-first-party` setting is restricted to `core` to ensure local modules are grouped correctly [pyproject.toml#67](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L67-L67)
-   Exclusions: Generated files like `ui_form.py` and large static data files like `app_icons.py` are excluded from analysis to prevent noise [pyproject.toml#42-50](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L42-L50)

### Vulture: Dead-Code Detection

Vulture is used to identify unused functions, classes, and variables. Due to the dynamic nature of Qt's signal/slot mechanism, Vulture is configured with a `min_confidence` of 80 [pyproject.toml#76](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L76-L76)

-   GUI False-Positives: Methods connected via `button.clicked.connect(self.method)` may be flagged as unused. Developers must verify these against `.ui` files and `connect()` calls before removal [docs/skills/python-cleanup-pyside6-4dach.md#87-103](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-pyside6-4dach.md?plain=1#L87-L103)
-   Whitelisting: Persistent false positives should be added to a `whitelist.py` generated via `vulture . --make-whitelist` [docs/SKILL.md#133-141](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L133-L141)

### deptry: Dependency Health

`deptry` monitors the health of the `pyproject.toml` dependencies, flagging unused, missing, or transitive dependencies [pyproject.toml#79-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L79-L86) It ignores specific dev-tools like `pytest-qt` and `ruff` which are required for the environment but not imported in the main application [pyproject.toml#85](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L85-L85)

### Tooling Execution Flow

Sources: [pyproject.toml#39-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/pyproject.toml#L39-L86) [.pre-commit-config.yaml#1-31](https://github.com/jooni22/4dach-qt/blob/81f560ca/.pre-commit-config.yaml#L1-L31) [docs/SKILL.md#9-19](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L9-L19)

___

## Review & Backlog Process

The project follows a "Review-First" implementation strategy. This ensures that feedback from previous Pull Requests (PRs) is addressed before new features are added.

### The Review Backlog (`docs/review-backlog.md`)

This file is the canonical source of truth for unresolved review guidance [docs/review-backlog.md#1-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/review-backlog.md?plain=1#L1-L7)

-   Status Lifecycle: Items move from `open` to `fixed`, `deferred`, `rejected`, or `stale` [docs/review-backlog.md#13-19](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/review-backlog.md?plain=1#L13-L19)
-   Triage Requirement: Before starting a task, agents/developers must check for unresolved items assigned to the current stage [AGENTS.md#100-110](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L100-L110)

### Review Synchronization Tools

Two scripts facilitate the flow of review data from GitHub to the local documentation:

1.  `scripts/export-pr-review.sh`: Fetches raw JSON data from GitHub for a specific PR.
2.  `scripts/sync-review-backlog.py`: Processes the raw JSON into a readable Markdown snapshot located in `docs/reviews/pr-XXX.md` [scripts/sync-review-backlog.py#1-7](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/sync-review-backlog.py#L1-L7)

### Review Data Flow

Sources: [docs/review-backlog.md#1-32](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/review-backlog.md?plain=1#L1-L32) [scripts/sync-review-backlog.py#1-24](https://github.com/jooni22/4dach-qt/blob/81f560ca/scripts/sync-review-backlog.py#L1-L24) [AGENTS.md#120-137](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L120-L137)

___

## Branching & Stacked PR Strategy

The repository utilizes a stage-based workflow to maintain a clean history and allow for incremental reviews.

### Branching Rules

-   No Direct Commits: Working directly on `main` or `master` is prohibited [AGENTS.md#72](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L72-L72)
-   Logical Isolation: Every implementation stage must reside on its own branch, focused on a single concern [AGENTS.md#73-75](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L73-L75)
-   Stacked PRs: If Stage B depends on Stage A, the branch for Stage B is created on top of Stage A's branch rather than `main` [AGENTS.md#76-77](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L76-L77)

### gh-stack Integration

The project supports the GitHub Stacked PR workflow through `gh-stack`. This tool is used to:

-   Initialize or continue a stack of branches.
-   Submit or update multiple related PRs simultaneously.
-   Sync the stack after a lower-level PR is merged into `main` [AGENTS.md#78-86](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L78-L86)

### Branching Hierarchy Diagram

Sources: [AGENTS.md#67-94](https://github.com/jooni22/4dach-qt/blob/81f560ca/AGENTS.md?plain=1#L67-L94) [docs/skills/python-cleanup-pyside6-4dach.md#61-81](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-pyside6-4dach.md?plain=1#L61-L81)

___

## Safety & Cleanup Protocol

When performing refactoring or "cleanup" tasks, specific safety measures are mandatory to prevent breaking the PySide6 application.

# Code Quality & Review Workflow

2.  Pre-flight Check: Verify `git status` is clean. Never run auto-fixers during a merge conflict [docs/skills/python-cleanup-pyside6-4dach.md#37-59](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-pyside6-4dach.md?plain=1#L37-L59)
3.  Ruff Resource Protection: Never remove imports ending in `_rc` (Qt resources). Use `# noqa: F401` if necessary to satisfy the linter [docs/SKILL.md#143-153](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L143-L153)
4.  Vulture Validation: Before deleting any method in a `QWidget` or `QObject` subclass, search for string references in `.ui` files and `connect()` calls [docs/SKILL.md#124-132](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L124-L132)
5.  Atomic Commits: Use `git add -p` to ensure cleanup changes are committed tool-by-tool (e.g., one commit for Ruff, one for Vulture) [docs/SKILL.md#104-112](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L104-L112)
6.  Mandatory Regression: `uv run pytest` must be executed after every cleanup pass [docs/SKILL.md#98-102](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L98-L102)

Sources: [docs/SKILL.md#67-120](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/SKILL.md?plain=1#L67-L120) [docs/skills/python-cleanup-pyside6-4dach.md#9-33](https://github.com/jooni22/4dach-qt/blob/81f560ca/docs/skills/python-cleanup-pyside6-4dach.md?plain=1#L9-L33) [.github/workflows/lint.yml#1-37](https://github.com/jooni22/4dach-qt/blob/81f560ca/.github/workflows/lint.yml#L1-L37)