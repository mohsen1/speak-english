#!/usr/bin/env bash
# Feed the hook a synthetic two-flush message and print what the screen would
# show. Exercises the real rewriter, so it costs one headless Claude call.
#
#   ./selftest.sh              # replace mode (the default)
#   SPEAK_ENGLISH_MODE=append ./selftest.sh
set -uo pipefail

# The hook is off unless /speak-english turned it on. The self-test exercises
# the rewriter either way, so it forces the switch for its own run only.
export SPEAK_ENGLISH_ENABLED="${SPEAK_ENGLISH_ENABLED:-1}"

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SELF_DIR/rewrite-display.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/head.txt" <<'EOF'
You're absolutely right to flag this — and it's a great question. Let me delve into the underlying architecture here.

Essentially, the feed background image job retry policy currently leverages a robust, comprehensive, and seamless exponential backoff strategy that plays a crucial role in ensuring that transient failures are handled gracefully. It's worth noting that the retries are capped at 5 attempts, which is fundamentally a pragmatic tradeoff.
EOF

cat > "$WORK/tail.txt" <<'EOF'

Furthermore, it's not just about retries — it's about the entire resilience landscape. The **key** insight is that the lock is acquired by the worker before the row is updated, which underscores the importance of the ordering.

```python
def retry(job):
    return backoff(job, attempts=5)
```

In conclusion, this approach may potentially streamline the overall pipeline.
EOF

flush() { # index final delta-file
  jq -n --arg i "$1" --arg f "$2" --rawfile d "$3" \
    '{session_id:"speak-english-selftest",transcript_path:"",cwd:".",
      hook_event_name:"MessageDisplay",turn_id:"selftest",message_id:"selftest-1",
      index:($i|tonumber),final:($f=="true"),delta:$d}' | "$HOOK"
}

# No output at all means the hook passed through, so the original delta stays on
# screen and that delta is what the terminal shows. An empty displayContent is a
# different result: it blanks the delta. Either way this prints the screen.
show() { # delta-file
  out="$(cat)"
  if [ -z "$out" ]; then
    echo "(pass-through, so the terminal shows:)"
    cat "$1"
  else
    printf '%s\n' "$out" | jq -r '.hookSpecificOutput.displayContent'
  fi
}

echo "--- flush 0 (streaming) ---"
flush 0 false "$WORK/head.txt" | show "$WORK/head.txt"

echo
echo "--- flush 1 (final) ---"
start=$(date +%s)
flush 1 true "$WORK/tail.txt" | show "$WORK/tail.txt"
echo
echo "--- rewriter wall time: $(( $(date +%s) - start ))s ---"
