# Codex Hooks

This repository uses repo-local Codex CLI hooks under `.codex/` to guard branch/task alignment at the end of a turn.

## Purpose

The previous stacked-PR reminder hooks were removed.

The active flow is now:

1. `UserPromptSubmit` stores a lightweight snapshot of the current branch, `HEAD`, dirty files, and the latest user prompt.
2. `Stop` checks whether the task described by that prompt still fits the current branch name.
3. If it does not fit, the hook creates a new branch named `feat/<task>` or `issue/<task>`, stages only files touched in the current turn, commits them, and pushes the branch to `origin`.

## Files

- `.codex/hooks.json`
- `.codex/hooks/branch_guard_common.py`
- `.codex/hooks/user_prompt_branch_snapshot.py`
- `.codex/hooks/stop_branch_guard.py`

## Enabling Hooks

Hooks are experimental and must be enabled in Codex config:

```toml
[features]
codex_hooks = true
```

Codex loads hooks from:

- `~/.codex/hooks.json`
- `<repo>/.codex/hooks.json`

This repository uses the repo-local location.

## Notes

- The hook commands resolve the repository root via `git rev-parse --show-toplevel`, so they work even when Codex starts in a subdirectory.
- Runtime snapshots are stored under `.git/codex-branch-guard/`, not in tracked files.
- Branch matching uses a conservative keyword overlap heuristic from the latest prompt. When no meaningful keywords are found, the hook leaves the current branch unchanged.
- If the current turn touches a file that was already dirty before the prompt, auto-commit/push is skipped for safety because the hook does not try to split mixed local edits.
- The stop hook never rewrites history. If commits already landed on the old branch during the turn, it only creates a new branch from the current `HEAD` and leaves the old branch untouched.
