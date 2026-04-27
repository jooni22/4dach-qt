#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from branch_guard_common import (
    branch_matches_prompt,
    classify_task,
    clear_snapshot,
    current_branch,
    current_head,
    detect_repo_root,
    dirty_paths,
    fingerprint_for_path,
    git,
    load_snapshot,
    proposed_branch_name,
    read_hook_input,
    task_keywords,
)


def output(message: str | None = None) -> int:
    payload: dict[str, Any] = {}
    if message:
        payload["systemMessage"] = message
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0


def touched_dirty_files(repo_root: Path, snapshot: dict[str, Any]) -> tuple[list[str], list[str]]:
    baseline = snapshot.get("dirty_files") or {}
    touched_clean: list[str] = []
    touched_preexisting_dirty: list[str] = []
    for path in dirty_paths(repo_root):
        current = fingerprint_for_path(repo_root, path)
        previous = baseline.get(path)
        if previous == current:
            continue
        if previous is None:
            touched_clean.append(path)
        else:
            touched_preexisting_dirty.append(path)
    return touched_clean, touched_preexisting_dirty


def committed_files_since_start(repo_root: Path, snapshot: dict[str, Any]) -> list[str]:
    start_head = snapshot.get("start_head")
    if not isinstance(start_head, str) or not start_head:
        return []
    now_head = current_head(repo_root)
    if not now_head or now_head == start_head:
        return []

    result = git(repo_root, "diff", "--name-only", "--diff-filter=ACMRTUXB", f"{start_head}..HEAD")
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            ordered.append(path)
            seen.add(path)
    return ordered


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def stage_paths(repo_root: Path, paths: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), "add", "-A", "--", *paths],
        capture_output=True,
        text=True,
        check=False,
    )


def create_branch_commit_and_push(
    repo_root: Path,
    prompt: str,
    paths: list[str],
    has_committed_changes: bool,
    included_preexisting_dirty: list[str],
) -> tuple[bool, str]:
    target_branch = proposed_branch_name(prompt, repo_root)
    current = current_branch(repo_root)

    if current != target_branch:
        switch_result = run_git(repo_root, "switch", "-c", target_branch)
        if switch_result.returncode != 0:
            return False, f"Branch mismatch detected, but `git switch -c {target_branch}` failed: {switch_result.stderr.strip() or switch_result.stdout.strip()}"

    stage_result = stage_paths(repo_root, paths)
    if stage_result.returncode != 0:
        return False, f"Switched to `{target_branch}`, but staging current-turn files failed: {stage_result.stderr.strip() or stage_result.stdout.strip()}"

    cached_diff = run_git(repo_root, "diff", "--cached", "--name-only")
    staged_paths = [line.strip() for line in cached_diff.stdout.splitlines() if line.strip()]
    current_turn_set = set(paths)
    staged_current_turn = [path for path in staged_paths if path in current_turn_set]
    if not staged_current_turn:
        if not has_committed_changes:
            return True, f"Branch mismatch detected. Switched to `{target_branch}`, but there were no net current-turn file changes to commit."
        push_result = run_git(repo_root, "push", "-u", "origin", target_branch)
        if push_result.returncode != 0:
            return False, f"Moved to `{target_branch}` at the current `HEAD`, but push failed: {push_result.stderr.strip() or push_result.stdout.strip()}"
        commit_sha = run_git(repo_root, "rev-parse", "--short", "HEAD").stdout.strip()
        return True, f"Branch mismatch detected. Created `{target_branch}` from the current `HEAD` ({commit_sha}) and pushed it to `origin`."

    _prefix, commit_type = classify_task(prompt)
    keywords = task_keywords(prompt)
    subject = "-".join(keywords[:4]) if keywords else "branch-guard-task"
    commit_message = f"{commit_type}: {subject}"

    commit_result = run_git(repo_root, "commit", "-m", commit_message, "--", *staged_current_turn)
    if commit_result.returncode != 0:
        return False, f"Switched to `{target_branch}` and staged current-turn files, but commit failed: {commit_result.stderr.strip() or commit_result.stdout.strip()}"

    push_result = run_git(repo_root, "push", "-u", "origin", target_branch)
    if push_result.returncode != 0:
        return False, f"Committed current-turn files on `{target_branch}`, but push failed: {push_result.stderr.strip() or push_result.stdout.strip()}"

    commit_sha = run_git(repo_root, "rev-parse", "--short", "HEAD").stdout.strip()
    warning = ""
    if included_preexisting_dirty:
        warning = (
            " Included files that were already dirty before the prompt but changed again in this turn: "
            + ", ".join(f"`{path}`" for path in included_preexisting_dirty)
            + "."
        )

    return True, (
        f"Branch mismatch detected. Moved current-turn changes to `{target_branch}`, committed as `{commit_message}` ({commit_sha}), and pushed to `origin`."
        + warning
    )


def main() -> int:
    payload = read_hook_input()
    repo_root = detect_repo_root(payload.get("cwd"))
    turn_id = payload.get("turn_id")

    if repo_root is None or not isinstance(turn_id, str) or not turn_id:
        return output()

    snapshot = load_snapshot(repo_root, turn_id)
    if snapshot is None:
        return output()

    try:
        prompt = snapshot.get("prompt")
        branch = current_branch(repo_root)

        if not isinstance(prompt, str) or not prompt.strip() or not branch:
            return output()

        if branch_matches_prompt(branch, prompt):
            return output()

        committed_files = committed_files_since_start(repo_root, snapshot)
        clean_dirty, preexisting_dirty = touched_dirty_files(repo_root, snapshot)
        touched = unique_paths(committed_files + clean_dirty + preexisting_dirty)
        if not touched:
            return output(
                f"Branch/task mismatch detected for `{branch}`, but no net current-turn file changes were found. No branch switch or push was performed."
            )

        ok, message = create_branch_commit_and_push(
            repo_root,
            prompt,
            touched,
            has_committed_changes=bool(committed_files),
            included_preexisting_dirty=preexisting_dirty,
        )
        return output(message)
    finally:
        clear_snapshot(repo_root, turn_id)


if __name__ == "__main__":
    raise SystemExit(main())
