#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

FIX_HINTS = {
    "bug",
    "bugfix",
    "error",
    "errors",
    "fix",
    "fixed",
    "fixes",
    "issue",
    "issues",
    "napraw",
    "naprawa",
    "naprawic",
    "problem",
    "problemy",
    "problemu",
    "regresja",
    "regression",
    "repair",
    "usterka",
    "blad",
    "błąd",
    "bledy",
    "błędy",
}

STOPWORDS = {
    "a",
    "aby",
    "add",
    "agent",
    "agenta",
    "aktualny",
    "and",
    "branch",
    "branchem",
    "branchu",
    "branchy",
    "brancha",
    "branches",
    "change",
    "changes",
    "check",
    "czy",
    "current",
    "currently",
    "dla",
    "do",
    "dodac",
    "dodaj",
    "end",
    "feat",
    "git",
    "go",
    "hook",
    "hooks",
    "i",
    "if",
    "issue",
    "it",
    "jego",
    "jezeli",
    "jeżeli",
    "ktory",
    "który",
    "ma",
    "message",
    "na",
    "napisze",
    "new",
    "nie",
    "nowy",
    "obecnie",
    "obecny",
    "oraz",
    "pasuje",
    "po",
    "pod",
    "prompt",
    "pr",
    "przez",
    "push",
    "repo",
    "server",
    "serwer",
    "sie",
    "się",
    "sprawdzac",
    "sprawdza",
    "sprawdzać",
    "stacked",
    "stop",
    "task",
    "tasku",
    "tego",
    "the",
    "to",
    "turn",
    "tworzy",
    "utworzy",
    "w",
    "will",
    "wykona",
    "wylacz",
    "wyłączy",
    "wysle",
    "wyśle",
    "zadania",
    "zadaniu",
    "zakonczonym",
    "zakończonym",
    "ze",
}


def read_hook_input() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def detect_repo_root(start_cwd: str | None) -> Path | None:
    cwd = Path(start_cwd or ".").resolve()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    stdout = result.stdout.strip()
    return Path(stdout).resolve() if stdout else None


def git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def git_ok(repo_root: Path, *args: str) -> str | None:
    result = git(repo_root, *args)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_branch(repo_root: Path) -> str | None:
    branch = git_ok(repo_root, "branch", "--show-current")
    return branch or None


def current_head(repo_root: Path) -> str | None:
    head = git_ok(repo_root, "rev-parse", "HEAD")
    return head or None


def parse_status_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status_output.splitlines():
        if len(raw_line) < 4:
            continue
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path)
    return paths


def dirty_paths(repo_root: Path) -> list[str]:
    result = git(repo_root, "status", "--short", "--untracked-files=all")
    if result.returncode != 0:
        return []
    return parse_status_paths(result.stdout)


def fingerprint_for_path(repo_root: Path, rel_path: str) -> str:
    path = repo_root / rel_path
    if not path.exists():
        return "missing"
    if path.is_symlink():
        return f"symlink:{path.readlink()}"
    if path.is_dir():
        return "dir"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"file:{digest}"


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def tokenize(text: str) -> list[str]:
    slug = slugify(text)
    tokens = [token for token in slug.split("-") if token]
    return tokens


def task_keywords(prompt: str, limit: int = 6) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for token in tokenize(prompt):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token.isdigit():
            continue
        if token not in seen:
            keywords.append(token)
            seen.add(token)
        if len(keywords) >= limit:
            break
    return keywords


def branch_tokens(branch: str) -> set[str]:
    ignored = {
        "feature",
        "feat",
        "fix",
        "hotfix",
        "issue",
        "bugfix",
        "chore",
        "task",
        "stage",
        "stages",
        "pr",
    }
    return {token for token in tokenize(branch) if token not in ignored and len(token) >= 3}


def classify_task(prompt: str) -> tuple[str, str]:
    prompt_tokens = set(tokenize(prompt))
    if prompt_tokens & {slugify(word) for word in FIX_HINTS}:
        return ("issue", "fix")
    return ("feat", "feat")


def proposed_branch_name(prompt: str, repo_root: Path) -> str:
    prefix, _commit_type = classify_task(prompt)
    keywords = task_keywords(prompt)
    base = "-".join(keywords[:5]) if keywords else f"{prefix}-task"
    base = base[:48].strip("-") or f"{prefix}-task"
    candidate = f"{prefix}/{base}"
    if current_branch(repo_root) == candidate:
        return candidate

    suffix = 2
    while git(repo_root, "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}").returncode == 0:
        candidate = f"{prefix}/{base}-{suffix}"
        suffix += 1
    return candidate


def branch_matches_prompt(branch: str, prompt: str) -> bool:
    tokens = task_keywords(prompt)
    if not tokens:
        return True
    branch_words = branch_tokens(branch)
    if not branch_words:
        return True
    overlap = branch_words.intersection(tokens)
    return bool(overlap)


def state_dir(repo_root: Path) -> Path:
    return repo_root / ".git" / "codex-branch-guard"


def snapshot_path(repo_root: Path, turn_id: str) -> Path:
    return state_dir(repo_root) / f"{turn_id}.json"


def load_snapshot(repo_root: Path, turn_id: str) -> dict[str, Any] | None:
    path = snapshot_path(repo_root, turn_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_snapshot(repo_root: Path, turn_id: str, prompt: str, payload: dict[str, Any]) -> None:
    directory = state_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "prompt": prompt,
        "saved_at": int(time.time()),
        **payload,
    }
    snapshot_path(repo_root, turn_id).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_snapshot(repo_root: Path, turn_id: str) -> None:
    path = snapshot_path(repo_root, turn_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return

