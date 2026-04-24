#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <owner/repo> <pr-number> [interval-seconds]"
  exit 1
fi

REPO="$1"
PR_NUMBER="$2"
INTERVAL="${3:-60}"

STATE_DIR="${TMPDIR:-/tmp}/gh-pr-watch"
mkdir -p "$STATE_DIR"

SAFE_REPO="${REPO//\//__}"
STATE_FILE="${STATE_DIR}/${SAFE_REPO}.json"
TMP_ERR="$(mktemp)"

cleanup_tmp() {
  rm -f "$TMP_ERR"
}
trap cleanup_tmp EXIT

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

is_pid_running() {
  local pid="${1:-}"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

print_previous_run_info() {
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "Previous run: none"
    return
  fi

  local last_repo last_pr last_pid last_status last_checked finished_at started_at
  last_repo="$(jq -r '.repo // ""' "$STATE_FILE")"
  last_pr="$(jq -r '.pr_number // ""' "$STATE_FILE")"
  last_pid="$(jq -r '.pid // ""' "$STATE_FILE")"
  last_status="$(jq -r '.status // ""' "$STATE_FILE")"
  last_checked="$(jq -r '.last_checked_at // ""' "$STATE_FILE")"
  started_at="$(jq -r '.started_at // ""' "$STATE_FILE")"
  finished_at="$(jq -r '.finished_at // empty' "$STATE_FILE")"

  echo "Previous run repo: ${last_repo:-unknown}"
  echo "Previous run PR: ${last_pr:-unknown}"
  echo "Previous run PID: ${last_pid:-unknown}"
  echo "Previous run status: ${last_status:-unknown}"
  echo "Previous run started_at: ${started_at:-unknown}"
  echo "Previous run last_checked_at: ${last_checked:-unknown}"

  if [[ -n "${last_pid:-}" ]] && [[ -z "${finished_at:-}" ]] && is_pid_running "$last_pid"; then
    echo "Previous run process state: RUNNING"
  else
    echo "Previous run process state: FINISHED"
    if [[ -n "${finished_at:-}" ]]; then
      echo "Previous run finished_at: ${finished_at}"
    fi
  fi
}

write_state() {
  local running="$1"
  local status="$2"
  local title="$3"
  local url="$4"
  local review_decision="$5"
  local merge_state_status="$6"
  local review_requests_json="$7"
  local pending_checks_json="$8"
  local failed_checks_json="$9"
  local note="${10}"
  local finished_at="${11:-null}"

  jq -n \
    --arg repo "$REPO" \
    --arg pr_number "$PR_NUMBER" \
    --arg pid "$$" \
    --arg started_at "${STARTED_AT}" \
    --arg last_checked_at "$(now_utc)" \
    --arg status "$status" \
    --arg title "$title" \
    --arg url "$url" \
    --arg review_decision "$review_decision" \
    --arg merge_state_status "$merge_state_status" \
    --arg note "$note" \
    --argjson running "$running" \
    --argjson review_requests "$review_requests_json" \
    --argjson pending_checks "$pending_checks_json" \
    --argjson failed_checks "$failed_checks_json" \
    --argjson finished_at "$finished_at" \
    '{
      repo: $repo,
      pr_number: ($pr_number | tonumber),
      pid: ($pid | tonumber),
      started_at: $started_at,
      last_checked_at: $last_checked_at,
      finished_at: $finished_at,
      running: $running,
      status: $status,
      title: $title,
      url: $url,
      review_decision: $review_decision,
      merge_state_status: $merge_state_status,
      review_requests: $review_requests,
      pending_checks: $pending_checks,
      failed_checks: $failed_checks,
      note: $note
    }' > "$STATE_FILE"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

require_cmd gh
require_cmd jq

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run: gh auth login"
  exit 1
fi

print_previous_run_info

if [[ -f "$STATE_FILE" ]]; then
  PREV_PID="$(jq -r '.pid // empty' "$STATE_FILE")"
  PREV_PR="$(jq -r '.pr_number // empty' "$STATE_FILE")"
  PREV_FINISHED="$(jq -r '.finished_at // empty' "$STATE_FILE")"

  if [[ -n "$PREV_PID" ]] && [[ -z "$PREV_FINISHED" ]] && is_pid_running "$PREV_PID" && [[ "$PREV_PR" == "$PR_NUMBER" ]]; then
    echo "A watcher for PR #$PR_NUMBER is already running with PID $PREV_PID"
    exit 0
  fi
fi

STARTED_AT="$(now_utc)"
LAST_SIGNATURE=""

echo "Starting watcher for ${REPO} PR #${PR_NUMBER}"
echo "Polling interval: ${INTERVAL}s"
echo "State file: ${STATE_FILE}"

finalize_and_exit() {
  local status="$1"
  local title="$2"
  local url="$3"
  local review_decision="$4"
  local merge_state_status="$5"
  local review_requests_json="$6"
  local pending_checks_json="$7"
  local failed_checks_json="$8"
  local note="$9"

  write_state "false" "$status" "$title" "$url" "$review_decision" "$merge_state_status" \
    "$review_requests_json" "$pending_checks_json" "$failed_checks_json" "$note" \
    "\"$(now_utc)\""

  echo "Final status: ${status}"
  echo "Finished."
  exit 0
}

trap 'echo "Interrupted."; if [[ -n "${LAST_TITLE:-}" ]]; then write_state "false" "INTERRUPTED" "${LAST_TITLE:-}" "${LAST_URL:-}" "${LAST_REVIEW_DECISION:-}" "${LAST_MERGE_STATE_STATUS:-}" "${LAST_REVIEW_REQUESTS_JSON:-[]}" "${LAST_PENDING_CHECKS_JSON:-[]}" "${LAST_FAILED_CHECKS_JSON:-[]}" "Process interrupted by signal." "\"$(now_utc)\""; fi; exit 130' INT TERM

while true; do
  : > "$TMP_ERR"
  set +e
  VIEW_JSON="$(gh pr view "$PR_NUMBER" -R "$REPO" --json title,url,state,reviewDecision,reviewRequests,mergeStateStatus 2>"$TMP_ERR")"
  VIEW_EXIT=$?
  set -e
  if [[ $VIEW_EXIT -ne 0 ]]; then
    echo "Failed to read PR details:"
    cat "$TMP_ERR" >&2
    exit $VIEW_EXIT
  fi

  : > "$TMP_ERR"
  set +e
  CHECKS_JSON="$(gh pr checks "$PR_NUMBER" -R "$REPO" --json name,state,bucket,workflow,link 2>"$TMP_ERR")"
  CHECKS_EXIT=$?
  set -e
  if [[ $CHECKS_EXIT -ne 0 && $CHECKS_EXIT -ne 8 ]]; then
    echo "Failed to read PR checks:"
    cat "$TMP_ERR" >&2
    exit $CHECKS_EXIT
  fi

  TITLE="$(jq -r '.title' <<< "$VIEW_JSON")"
  URL="$(jq -r '.url' <<< "$VIEW_JSON")"
  PR_STATE="$(jq -r '.state // "UNKNOWN"' <<< "$VIEW_JSON")"
  REVIEW_DECISION="$(jq -r '.reviewDecision // "UNKNOWN"' <<< "$VIEW_JSON")"
  MERGE_STATE_STATUS="$(jq -r '.mergeStateStatus // "UNKNOWN"' <<< "$VIEW_JSON")"

  REVIEW_REQUESTS_JSON="$(jq -c '
    (.reviewRequests // [])
    | map({
        name: (.login // .name // .slug // "unknown"),
        type: (.type // .__typename // "unknown"),
        is_bot: (((.login // .name // .slug // "") | test("\\[bot\\]$|bot"; "i")) // false)
      })
  ' <<< "$VIEW_JSON")"

  PENDING_CHECKS_JSON="$(jq -c '
    [ .[] | select(.bucket == "pending") | {
        name: (.name // "unknown"),
        workflow: (.workflow // "unknown"),
        state: (.state // "unknown"),
        link: (.link // "")
      } ]
  ' <<< "$CHECKS_JSON")"

  FAILED_CHECKS_JSON="$(jq -c '
    [ .[] | select(.bucket == "fail" or .bucket == "cancel") | {
        name: (.name // "unknown"),
        workflow: (.workflow // "unknown"),
        state: (.state // "unknown"),
        link: (.link // "")
      } ]
  ' <<< "$CHECKS_JSON")"

  PENDING_CHECKS_COUNT="$(jq 'length' <<< "$PENDING_CHECKS_JSON")"
  FAILED_CHECKS_COUNT="$(jq 'length' <<< "$FAILED_CHECKS_JSON")"
  REVIEW_REQUESTS_COUNT="$(jq 'length' <<< "$REVIEW_REQUESTS_JSON")"

  HAS_PENDING_REVIEW="false"
  if [[ "$REVIEW_REQUESTS_COUNT" -gt 0 ]]; then
    HAS_PENDING_REVIEW="true"
  elif [[ "$REVIEW_DECISION" == "REVIEW_REQUIRED" ]]; then
    HAS_PENDING_REVIEW="true"
  fi

  STATUS="READY"
  NOTE="PR is ready."

  if [[ "$PR_STATE" != "OPEN" ]]; then
    STATUS="BLOCKED"
    NOTE="PR is not open."
  elif [[ "$REVIEW_DECISION" == "CHANGES_REQUESTED" ]]; then
    STATUS="BLOCKED"
    NOTE="Changes were requested in review."
  elif [[ "$FAILED_CHECKS_COUNT" -gt 0 ]]; then
    STATUS="BLOCKED"
    NOTE="One or more checks failed or were cancelled."
  elif [[ "$PENDING_CHECKS_COUNT" -gt 0 ]]; then
    STATUS="PENDING_CHECKS"
    NOTE="Checks are still pending."
  elif [[ "$HAS_PENDING_REVIEW" == "true" ]]; then
    STATUS="PENDING_REVIEW"
    NOTE="Review is still pending."
  fi

  LAST_TITLE="$TITLE"
  LAST_URL="$URL"
  LAST_REVIEW_DECISION="$REVIEW_DECISION"
  LAST_MERGE_STATE_STATUS="$MERGE_STATE_STATUS"
  LAST_REVIEW_REQUESTS_JSON="$REVIEW_REQUESTS_JSON"
  LAST_PENDING_CHECKS_JSON="$PENDING_CHECKS_JSON"
  LAST_FAILED_CHECKS_JSON="$FAILED_CHECKS_JSON"

  SIGNATURE="$(jq -nc \
    --arg status "$STATUS" \
    --arg review_decision "$REVIEW_DECISION" \
    --arg merge_state_status "$MERGE_STATE_STATUS" \
    --argjson review_requests "$REVIEW_REQUESTS_JSON" \
    --argjson pending_checks "$PENDING_CHECKS_JSON" \
    --argjson failed_checks "$FAILED_CHECKS_JSON" \
    '{
      status: $status,
      review_decision: $review_decision,
      merge_state_status: $merge_state_status,
      review_requests: $review_requests,
      pending_checks: $pending_checks,
      failed_checks: $failed_checks
    }'
  )"

  write_state "true" "$STATUS" "$TITLE" "$URL" "$REVIEW_DECISION" "$MERGE_STATE_STATUS" \
    "$REVIEW_REQUESTS_JSON" "$PENDING_CHECKS_JSON" "$FAILED_CHECKS_JSON" "$NOTE"

  if [[ "$SIGNATURE" != "$LAST_SIGNATURE" ]]; then
    echo "------------------------------------------------------------"
    echo "Time: $(now_utc)"
    echo "Repo: $REPO"
    echo "PR: #$PR_NUMBER"
    echo "Title: $TITLE"
    echo "URL: $URL"
    echo "Status: $STATUS"
    echo "PR state: $PR_STATE"
    echo "Review decision: $REVIEW_DECISION"
    echo "Merge state status: $MERGE_STATE_STATUS"

    echo "Pending review requests:"
    jq -r '
      if length == 0 then
        "  none"
      else
        .[] | "  - \(.name) [type=\(.type)] [bot=\(.is_bot)]"
      end
    ' <<< "$REVIEW_REQUESTS_JSON"

    echo "Pending checks:"
    jq -r '
      if length == 0 then
        "  none"
      else
        .[] | "  - \(.workflow) / \(.name) [state=\(.state)]"
      end
    ' <<< "$PENDING_CHECKS_JSON"

    echo "Failed checks:"
    jq -r '
      if length == 0 then
        "  none"
      else
        .[] | "  - \(.workflow) / \(.name) [state=\(.state)]"
      end
    ' <<< "$FAILED_CHECKS_JSON"
  else
    echo "No change at $(now_utc); current status: $STATUS"
  fi

  LAST_SIGNATURE="$SIGNATURE"

  if [[ "$STATUS" == "READY" || "$STATUS" == "BLOCKED" ]]; then
    finalize_and_exit "$STATUS" "$TITLE" "$URL" "$REVIEW_DECISION" "$MERGE_STATE_STATUS" \
      "$REVIEW_REQUESTS_JSON" "$PENDING_CHECKS_JSON" "$FAILED_CHECKS_JSON" "$NOTE"
  fi

  sleep "$INTERVAL"
done