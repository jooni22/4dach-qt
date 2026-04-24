# AGENTS.md
# Instructions for AI Agents and Developers

This project uses **uv** for environment management and strictly requires **Python 3.11**.  
To avoid dependency and interpreter mismatches, always follow the rules below.

---

## 1. Environment and Python version

- The virtual environment is located in `.venv`.
- If the shell supports it (for example through `direnv`), the environment may be activated automatically via `.envrc`.
- If the environment is not activated automatically, **always use the `uv run` prefix**. This guarantees the correct Python 3.11 interpreter.

---

## 2. Running the project

To run the application or the main entry point, use:

```bash
uv run python3 __main__.py
```

Running plain `python3` is only acceptable if the virtual environment has already been activated manually, for example with:

```bash
source .venv/bin/activate
```

---

## 3. Running tests

The project uses `pytest` and `pytest-qt` for GUI testing with PySide6.

To run the full test suite:

```bash
uv run pytest
```

If you need to run a smaller subset of tests, still prefer `uv run`, for example:

```bash
uv run pytest tests/test_canvas_mapper.py
```

---

## 4. Adding dependencies

Project dependencies are managed with **uv**.  
Do not use plain `pip install` unless explicitly instructed.

Add packages like this:

```bash
uv add package_name
uv add --dev dev_package_name
```

Using `uv run` and `uv add` ensures the project remains isolated and reproducible.

---

## 5. Branching and stacked PR workflow

This repository uses a **stage-based workflow** and should support **stacked pull requests**.

### Rules
- Never work directly on `master` / `main`.
- Every implementation stage should be done on its own branch.
- Prefer **stacked branches / stacked PRs** for sequential stages.
- Keep each branch focused on **one logical concern** only.
- If a new stage depends on the previous stage, create it on top of the previous branch instead of branching again from `master`.

### gh-stack
This repository may use the GitHub Stacked PR workflow through `gh-stack`.

If available in the current environment, use it to:
- initialize or continue the current stack
- create the next stage branch in the stack
- submit or update stacked PRs
- sync the stack after lower PRs are merged

Preferred behavior:
- At the start of a new stage, determine whether the current work belongs in the existing stack.
- At the end of a stage, update the stack and PRs rather than creating unrelated standalone PRs.

Do not invent a stack layout if the current branch strategy already exists in the repository.  
Instead, inspect the existing local branches and current PR naming conventions first.

---

## 6. Review comment workflow

This project should preserve useful AI/code-review feedback across stages.

### Required behavior before implementation
Before starting any new implementation task, an agent must:
1. Read `AGENTS.md`
2. Read `docs/review-backlog.md` if it exists
3. Check whether there are unresolved review items assigned to the current stage
4. Decide which items should be:
   - fixed now
   - fixed during the current implementation
   - deferred to a later stage
   - marked stale / no longer applicable

### Required behavior after implementation
Before finalizing a stage branch or updating its PR, an agent should:
1. Run relevant tests
2. Review unresolved backlog items related to modified files
3. Apply safe and local fixes
4. Leave deferred items clearly documented

---

## 7. Review backlog rules

If `docs/review-backlog.md` exists, treat it as the persistent source of unresolved review guidance.

### Status meanings
- `open` — should still be considered
- `fixed` — already resolved in code
- `deferred` — intentionally postponed to a later stage
- `rejected` — reviewed and intentionally not adopted
- `stale` — no longer relevant after later code changes

### Agent behavior
- Resolve `open` items for the current stage when they are low-risk and local.
- Do not automatically implement `deferred`, `rejected`, or `stale` items unless explicitly instructed.
- If a previously open item is no longer relevant, mark it `stale` with a short explanation.
- If an item is clearly out of scope for the current stage, keep it deferred and do not expand the task unnecessarily.

---

## 8. Scope discipline

When implementing a stage:
- Do only the work needed for that stage
- Do not rewrite unrelated architecture without a strong reason
- Do not silently change persistence formats unless required
- Do not mix Qt/UI logic into pure domain logic inside `core/`
- Keep business logic testable and, where possible, Qt-free
- Extend existing modules incrementally instead of replacing them wholesale unless explicitly requested

---

## 9. Testing expectations

For every meaningful change:
- run relevant tests with `uv run pytest`
- add tests for new domain logic where practical
- avoid shipping untested geometry/layout behavior
- prefer small, reviewable commits over large monolithic changes

If a GUI behavior changes, add either:
- direct unit tests where possible, or
- a clear manual QA note in the final summary

---

## 10. Expected final response from an agent

When finishing a task, provide a concise implementation summary including:
- what was changed
- which files were modified
- whether tests were run and with what result
- whether stacked PR workflow actions were taken
- whether review-backlog items were resolved, deferred, or left untouched

Do not claim that a PR was created unless it was actually created.
Do not claim that review comments were synchronized unless that step was actually executed.

---

## 11. Safe defaults

If anything about the workflow is unclear:
- prefer preserving the current branch structure
- prefer small incremental changes
- prefer documenting uncertainty instead of guessing
- prefer reading existing repo files before introducing new automation