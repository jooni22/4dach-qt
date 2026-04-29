#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/cleanup_preview.sh [options]

Creates an isolated git worktree, runs cleanup tools there, and writes reports
and a patch diff without modifying the current working tree.

Options:
  --base-ref REF          Git ref to preview from (default: HEAD)
  --reports-dir DIR       Report directory (default: reports/cleanup-preview/<timestamp>)
  --worktree-dir DIR      Worktree directory (default: /tmp/4dach-cleanup-preview-<timestamp>-<pid>)
  --ruff-select CODES     Ruff rules for the preview fix pass (default: F,I)
  --skip-tests            Do not run pytest in the preview worktree
  --remove-worktree       Remove the preview worktree when the script exits
  -h, --help              Show this help

Important:
  The preview uses the committed state of --base-ref. Uncommitted changes and
  conflicts in the current working tree are recorded in reports but are not
  copied into the preview worktree.
EOF
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

now_stamp() {
  date -u +"%Y%m%dT%H%M%SZ"
}

quote_command() {
  printf '%q ' "$@"
}

run_capture() {
  local name="$1"
  shift
  local logfile="${report_dir}/${name}.txt"
  printf '\n[%s]\n' "$name" >>"${report_dir}/commands.log"
  quote_command "$@" >>"${report_dir}/commands.log"
  printf '\n' >>"${report_dir}/commands.log"
  printf 'Running %-28s -> %s\n' "$name" "$logfile"
  set +e
  (cd "$worktree_dir" && "$@") >"$logfile" 2>&1
  local status=$?
  set -e
  printf '%s\t%s\t%s\n' "$name" "$status" "$logfile" >>"${report_dir}/command-status.tsv"
  return 0
}

base_ref="HEAD"
report_dir=""
worktree_dir=""
ruff_select="F,I"
run_tests=1
remove_worktree=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-ref)
      [[ $# -ge 2 ]] || fail "--base-ref requires a value"
      base_ref="$2"
      shift 2
      ;;
    --reports-dir)
      [[ $# -ge 2 ]] || fail "--reports-dir requires a value"
      report_dir="$2"
      shift 2
      ;;
    --worktree-dir)
      [[ $# -ge 2 ]] || fail "--worktree-dir requires a value"
      worktree_dir="$2"
      shift 2
      ;;
    --ruff-select)
      [[ $# -ge 2 ]] || fail "--ruff-select requires a value"
      ruff_select="$2"
      shift 2
      ;;
    --skip-tests)
      run_tests=0
      shift
      ;;
    --remove-worktree)
      remove_worktree=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1"
      ;;
  esac
done

command -v git >/dev/null 2>&1 || fail "git is required"
command -v uv >/dev/null 2>&1 || fail "uv is required"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "not inside a git repository"
timestamp="$(now_stamp)"

if [[ -z "$report_dir" ]]; then
  report_dir="${repo_root}/reports/cleanup-preview/${timestamp}"
elif [[ "$report_dir" != /* ]]; then
  report_dir="${repo_root}/${report_dir}"
fi

if [[ -z "$worktree_dir" ]]; then
  worktree_dir="${TMPDIR:-/tmp}/4dach-cleanup-preview-${timestamp}-$$"
elif [[ "$worktree_dir" != /* ]]; then
  worktree_dir="${repo_root}/${worktree_dir}"
fi

mkdir -p "$report_dir"
: >"${report_dir}/commands.log"
: >"${report_dir}/command-status.tsv"
printf 'name\texit_code\tlogfile\n' >"${report_dir}/command-status.tsv"

git -C "$repo_root" rev-parse --verify --quiet "$base_ref^{commit}" >/dev/null || fail "base ref not found: ${base_ref}"

cleanup() {
  if [[ "$remove_worktree" -eq 1 && -d "$worktree_dir" ]]; then
    git -C "$repo_root" worktree remove --force "$worktree_dir" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

{
  printf '# Cleanup Preview Metadata\n\n'
  printf -- '- Repository: `%s`\n' "$repo_root"
  printf -- '- Base ref: `%s`\n' "$base_ref"
  printf -- '- Timestamp UTC: `%s`\n' "$timestamp"
  printf -- '- Report dir: `%s`\n' "$report_dir"
  printf -- '- Worktree dir: `%s`\n' "$worktree_dir"
  printf -- '- Ruff preview select: `%s`\n' "$ruff_select"
  printf -- '- Remove worktree on exit: `%s`\n' "$remove_worktree"
  printf -- '- Run tests: `%s`\n\n' "$run_tests"
  printf '## Current working tree status\n\n```text\n'
  git -C "$repo_root" status --short || true
  printf '```\n\n'
  printf '## Current stash list\n\n```text\n'
  git -C "$repo_root" stash list --date=local || true
  printf '```\n'
} >"${report_dir}/metadata.md"

git -C "$repo_root" archive --format=tar.gz --output "${report_dir}/source-${timestamp}.tar.gz" "$base_ref"

git -C "$repo_root" worktree add --detach "$worktree_dir" "$base_ref" >"${report_dir}/worktree-add.txt" 2>&1

run_capture uv-sync uv sync
run_capture ruff-check-before uv run --with ruff ruff check .
run_capture ruff-format-diff-before uv run --with ruff ruff format --diff .
run_capture vulture-report uv run --with vulture vulture .
run_capture deptry-report uv run --with deptry deptry .
run_capture ruff-fix-preview uv run --with ruff ruff check . --select "$ruff_select" --fix
run_capture ruff-format-preview uv run --with ruff ruff format .

if [[ "$run_tests" -eq 1 ]]; then
  run_capture pytest-after-preview uv run pytest
fi

(
  cd "$worktree_dir"
  git status --short >"${report_dir}/git-status-after-preview.txt"
  git diff --stat >"${report_dir}/cleanup-preview.diffstat"
  git diff --binary >"${report_dir}/cleanup-preview.diff"
)

{
  printf '# Cleanup Preview Summary\n\n'
  printf -- '- Report directory: `%s`\n' "$report_dir"
  printf -- '- Preview worktree: `%s`\n' "$worktree_dir"
  printf -- '- Source archive: `%s`\n' "${report_dir}/source-${timestamp}.tar.gz"
  printf -- '- Patch diff: `%s`\n' "${report_dir}/cleanup-preview.diff"
  printf -- '- Diff stat: `%s`\n\n' "${report_dir}/cleanup-preview.diffstat"
  printf '## Command statuses\n\n'
  printf '| Command | Exit code | Log |\n'
  printf '| --- | ---: | --- |\n'
  tail -n +2 "${report_dir}/command-status.tsv" | while IFS=$'\t' read -r name status logfile; do
    printf '| `%s` | `%s` | `%s` |\n' "$name" "$status" "$logfile"
  done
  printf '\n## Changed files in preview worktree\n\n```text\n'
  cat "${report_dir}/git-status-after-preview.txt"
  printf '```\n\n'
  printf '## Diff stat\n\n```text\n'
  cat "${report_dir}/cleanup-preview.diffstat"
  printf '```\n'
} >"${report_dir}/summary.md"

tar -czf "${report_dir}.tar.gz" -C "$(dirname "$report_dir")" "$(basename "$report_dir")"

printf '\nCleanup preview complete.\n'
printf 'Reports: %s\n' "$report_dir"
printf 'Archive: %s.tar.gz\n' "$report_dir"
printf 'Diff: %s\n' "${report_dir}/cleanup-preview.diff"
printf 'Summary: %s\n' "${report_dir}/summary.md"
if [[ "$remove_worktree" -eq 0 ]]; then
  printf 'Preview worktree kept at: %s\n' "$worktree_dir"
  printf 'Remove it later with: git worktree remove --force %q\n' "$worktree_dir"
fi
