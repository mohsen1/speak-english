"""Regenerate evals/results.json.

Four arms over the same prompts, so the question "does an instruction do the
job instead of a rewrite?" is answered with output rather than opinion:

  no-guide                  plain `claude -p`
  guide-injected            the style guide as --system-prompt
  injected-then-rewritten   that output, through the hook
  rewriter-only             the no-guide output, through the hook

Needs `claude` on PATH and logged in. Costs one call per prompt per arm, plus
one rewrite per prompt for each rewritten arm.

    python3 evals/run.py && python3 evals/score.py evals/results.json
"""

import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "rewrite-display.sh"
STYLE = (ROOT / "style" / "plain-english.md").read_text()
PROMPTS = [p for p in (ROOT / "evals" / "prompts.txt").read_text().splitlines() if p.strip()]
MODEL = os.environ.get("SPEAK_ENGLISH_EVAL_MODEL", "sonnet")

AUTHOR_SYSTEM = "Follow this style guide for every message you write.\n\n" + STYLE


def ask(prompt, system=None):
    cmd = ["claude", "-p", "--model", MODEL]
    if system:
        cmd += ["--system-prompt", system]
    cmd.append(prompt)
    # The hook is disabled for the arms that are supposed to be unrewritten.
    env = {**os.environ, "SPEAK_ENGLISH_ENABLED": "0"}
    return subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp", env=env).stdout.strip()


def through_hook(text, tag):
    """Feed one finished message through the real MessageDisplay protocol."""
    payload = json.dumps({
        "session_id": "evals", "transcript_path": "", "cwd": ".",
        "hook_event_name": "MessageDisplay", "turn_id": tag,
        "message_id": tag, "index": 0, "final": True, "delta": text,
    })
    env = {**os.environ, "SPEAK_ENGLISH_ENABLED": "1"}
    r = subprocess.run([str(HOOK)], input=payload, capture_output=True, text=True,
                       cwd="/tmp", env=env)
    if not r.stdout.strip():
        return text  # pass-through leaves the original on screen
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["displayContent"]
    except Exception:
        return text


def each(fn, items):
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(fn, items))


plain = each(ask, PROMPTS)
injected = each(lambda p: ask(p, AUTHOR_SYSTEM), PROMPTS)
arms = {
    "no-guide": plain,
    "guide-injected": injected,
    "rewriter-only": each(lambda t: through_hook(t[1], f"r{t[0]}"), list(enumerate(plain))),
    "injected-then-rewritten": each(lambda t: through_hook(t[1], f"i{t[0]}"), list(enumerate(injected))),
}

(ROOT / "evals" / "results.json").write_text(json.dumps(
    {"model": MODEL, "note": "one-shot claude -p", "prompts": PROMPTS, "arms": arms}, indent=1))
print("wrote evals/results.json")
