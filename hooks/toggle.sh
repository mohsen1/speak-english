#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# State for the display rewriter, behind /speak-english.
#
#   on             rewrite assistant messages from the next message
#   off            stop rewriting
#   append         show the original and put the rewrite under it
#   replace        show the rewrite in place of the original (default)
#   status, none   report the current state
#
# The state is two files under $CLAUDE_CONFIG_DIR, read fresh by the hook once
# per message, so a change applies from the next message without restarting the
# session. Env vars cannot do that: they are frozen when the session launches.
# ---------------------------------------------------------------------------
set -uo pipefail

CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
ON_FILE="${SPEAK_ENGLISH_ON_FILE:-$CFG/speak-english-on}"
MODE_FILE="${SPEAK_ENGLISH_MODE_FILE:-$CFG/speak-english-mode}"

# The state files are configurable, so their parents are not always $CFG.
mkdir -p "$CFG" "$(dirname "$ON_FILE")" "$(dirname "$MODE_FILE")" 2>/dev/null || true

read_mode() {
  [ -f "$MODE_FILE" ] || { printf 'replace'; return; }
  case "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" in
    append) printf 'append' ;;
    *)      printf 'replace' ;;
  esac
}

status() {
  if [ -f "$ON_FILE" ]; then
    printf 'speak-english is ON, mode %s\n' "$(read_mode)"
  else
    printf 'speak-english is OFF\n'
  fi
}

# Quoted at the call site, so no argument arrives as an empty string.
action="${1:-}"
[ -n "$action" ] || action=status

case "$action" in
  on)
    : > "$ON_FILE" || { echo "cannot write $ON_FILE" >&2; exit 1; }
    printf 'speak-english ON from the next message, mode %s\n' "$(read_mode)"
    ;;
  off)
    rm -f "$ON_FILE"
    # Reporting "off" while the marker survives would be a lie the reader pays
    # for, one rewrite at a time.
    if [ -e "$ON_FILE" ]; then
      printf 'cannot remove %s, so speak-english is still ON\n' "$ON_FILE" >&2
      exit 1
    fi
    printf 'speak-english OFF from the next message. Messages already on screen keep the form they were shown in.\n'
    ;;
  append|replace)
    printf '%s\n' "$action" > "$MODE_FILE" || { echo "cannot write $MODE_FILE" >&2; exit 1; }
    if [ -f "$ON_FILE" ]; then
      printf 'mode %s from the next message\n' "$action"
    else
      printf 'mode %s saved. speak-english is OFF, so run /speak-english on to use it.\n' "$action"
    fi
    ;;
  status)
    status
    ;;
  *)
    printf 'usage: /speak-english on|off|append|replace|status\n' >&2
    status
    exit 1
    ;;
esac
