# Codex Hooks

This repository includes a minimal repo-local Codex CLI hooks setup under `.codex/`.

## Purpose

The hooks are advisory only. They do not edit files, change branches, or block work.

They surface repository workflow context so Codex is reminded to:

- read `AGENTS.md`
- read `docs/review-backlog.md` when it exists
- check the current branch
- consider unresolved review-backlog items before implementation

## Files

- `.codex/hooks.json`
- `.codex/hooks/session_start_review_context.py`
- `.codex/hooks/user_prompt_review_context.py`

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

- The hook commands resolve the repository root via `git rev-parse --show-toplevel` so they still work when Codex is started from a subdirectory.
- Open backlog items are counted with a minimal heuristic that only scans the `## Open Items` section and counts rows whose status column is `open`.
- If the session is not inside a git repository, the hooks return a safe reminder instead of failing closed.
