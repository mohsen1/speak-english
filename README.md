# speak-english

A Claude Code plugin that rewrites each finished assistant message into plain
English before it reaches your screen.

The rewriter is Claude Code itself, run headless (`claude -p`) against the login
you already have. No API key, no local model server, no third-party provider.

It is off until you ask for it:

```
/plugin marketplace add mohsen1/speak-english
/plugin install speak-english
/speak-english on
```

## What it changes

Your screen. The stored transcript, the conversation the model sees, and every
other consumer keep the original text.

Before:

> You're absolutely right to flag this, and it's a great question. Let me delve
> into the underlying architecture here.
>
> Essentially, the feed background image job retry policy currently leverages a
> robust, comprehensive, and seamless exponential backoff strategy that plays a
> crucial role in ensuring that transient failures are handled gracefully. It's
> worth noting that the retries are capped at 5 attempts, which is fundamentally
> a pragmatic tradeoff.

After:

> The retry policy for feed background image jobs uses exponential backoff to
> handle transient failures. Retries are capped at 5 attempts.

## Why a rewriter and not an instruction

The obvious design is to hand the model a style guide up front and let it write
to the guide. That was built and measured, and it does not work. Eight dev
questions, sonnet, one-shot `claude -p`, counting the guide's own tells by regex
with code fences excluded:

| Arm                     | Total tells | Em dashes | Bold | Headings | Chars  |
| ----------------------- | ----------- | --------- | ---- | -------- | ------ |
| no guide                | 79          | 36        | 41   | 1        | 14,563 |
| guide injected up front | 54          | 9         | 37   | 8        | 15,778 |
| injected and rewritten  | 41          | 1         | 32   | 8        | 15,159 |
| rewriter only, ships    | **16**      | 2         | 12   | 1        | 13,792 |

An instruction removes the words it names and nothing else. It does not shorten
the answer, and every variant tried made the model reach for more structure:
injecting the guide took headings from 1 to 8 and added 1,200 characters. A
short guide naming only the tells was worse again, at 20 em dashes and 28% more
text than no instruction at all.

Injecting and then rewriting is worse than rewriting alone, because the rewriter
respects the shape of what it is given, so it preserves the headings the
instruction provoked.

The rewriter is the only arm that cut length against its own input. An editor
with no task can only delete.

Full table, per-prompt character counts, and one answer shown through every arm:
[`evals/RESULTS.md`](evals/RESULTS.md).

Reproduce it:

```bash
python3 evals/run.py
python3 evals/score.py evals/results.json                        # terminal
python3 evals/score.py evals/results.json --markdown > evals/RESULTS.md
```

Sample size is 8 one-shot answers to generic questions, so read it as
directional. The baseline scored zero praise openers and zero inflated
vocabulary, which means the run barely exercises the tells that show up after
twenty turns of real work.

## Commands

```
/speak-english on        # rewrite from the next message
/speak-english off       # stop
/speak-english append    # keep the original and put the rewrite under it
/speak-english replace   # show the rewrite in place of the original (default)
/speak-english status    # report the current state
```

The state lives in `~/.claude/speak-english-on` and
`~/.claude/speak-english-mode`. The hook reads both once per message, on its
first flush, so a change applies from the next message. A message that is
already streaming finishes under the setting it started with, because `replace`
mode blanks every non-final flush and a switch taken mid-message would leave the
hidden deltas unreachable.

Nothing you type reaches a shell. The command file runs no inline command, and
`toggle.sh` matches its argument against those five words and rejects anything
else without evaluating it.

## Your own style guide

The rewriter follows the first of these that exists:

1. `SPEAK_ENGLISH_STYLE_FILE`
2. `.claude/speak-english-style.md` in the project
3. [`style/plain-english.md`](style/plain-english.md), shipped with the plugin

A project guide replaces the default outright. It does not need to restate the
editor contract, which lives in the hook: the rewriter is told there that it is
an editor and not an author, that it may not answer the question, and that it may
not add or remove a fact.

The default takes its rules from
[claudish-to-english](https://github.com/gvzdv/claudish-to-english), which
catalogues the tells, and from ASD-STE100 Simplified Technical English, which
supplies the sentence rules.

## How it works

`MessageDisplay` fires once per flush of completed lines while a message
streams, each fire a separate process carrying `.message_id`, `.index`, `.final`
and `.delta`. `rewrite-display.sh` writes every delta to a buffer directory
under `$TMPDIR` and, on the final flush, reassembles the message and rewrites it
in one headless call.

```
flush 0..n-1  ──▶  delta buffered under $TMPDIR    (replace mode: screen blanked)
flush n       ──▶  reassemble ──▶ claude -p ──▶ guards ──▶ screen
                                                  │
                                                  └── any guard fails ──▶ original
```

The hook fails open. A missing `jq` or `claude`, an unreadable guide, a timeout,
or an empty rewrite leaves the original on screen, and in `replace` mode that
means the whole buffered message, not just the last delta.

Four things stop a rewrite that did come back:

- it is more than twice the length of the original;
- a fenced code block differs by a single byte, fence lines included;
- an inline `` `...` `` span from the original is missing;
- a span appears whose text is nowhere in the original.

The span check compares text, not markup, so promoting a command from bold to
code passes. Dropping one does not: a message that loses one of two commands
still reads as a complete instruction, and `replace` mode leaves no original on
screen to check it against.

A message that parses as JSON never reaches the rewriter, because its exact keys
and values are the answer.

## What nothing checks

The prose. The editor contract forbids adding information and says so twice, and
the rewriter still sometimes supplies a reason the message did not give. On the
self-test message that happened in 1 of 3 runs, producing a plausible and
probably correct clause that the assistant never wrote.

That is the cost of the design. A rewrite that passes all four guards but adds a
claim, or softens a caveat, is what you read, and the original is then only in
the transcript. `/speak-english append` keeps both on screen if that trade is not
worth it to you.

## Cost and latency

One headless call per qualifying message, billed to the same subscription as the
session. Measured on the self-test message, about 830 characters:

| Rewriter           | Wall time | Cost    |
| ------------------ | --------- | ------- |
| `sonnet` (default) | 3-6s      | ~$0.015 |
| `haiku`            | 80-90s    | ~$0.044 |

Haiku 4.5 is not the cheap option here. It spends 8,000+ thinking tokens on a
rewrite and ignores `--effort low`.

In `replace` mode that wall time is dead air: nothing shows until the message is
finished and rewritten. Messages under 200 characters of prose (code excluded)
and over 16,000 characters are passed through untouched.

## Configuration

| Variable                   | Default                      | Meaning                                            |
| -------------------------- | ---------------------------- | -------------------------------------------------- |
| `SPEAK_ENGLISH_ENABLED`    | unset                        | `1` or `0` forces the answer and beats the on-file. |
| `SPEAK_ENGLISH_ON_FILE`    | `~/.claude/speak-english-on` | Exists means on. Written by `/speak-english`.       |
| `SPEAK_ENGLISH_STYLE_FILE` | see above                    | The style guide.                                    |
| `SPEAK_ENGLISH_MODE`       | `replace`                    | `replace` or `append`.                              |
| `SPEAK_ENGLISH_MODE_FILE`  | `~/.claude/speak-english-mode` | Live mode. Written by `/speak-english`.           |
| `SPEAK_ENGLISH_MODEL`      | `sonnet`                     | Rewriter model.                                     |
| `SPEAK_ENGLISH_MIN_CHARS`  | `200`                        | Skip shorter messages (prose only).                 |
| `SPEAK_ENGLISH_MAX_CHARS`  | `16000`                      | Skip longer messages.                               |
| `SPEAK_ENGLISH_TIMEOUT`    | `45`                         | Rewriter timeout in seconds.                        |
| `SPEAK_ENGLISH_DEBUG`      | `0`                          | Log to `$TMPDIR/claude-speak-english-$UID/debug.log`. |

Environment variables freeze when the session launches, so they are for scripts.
`/speak-english` is the live switch.

## Isolation

The rewriter runs with `--tools ""`, `--strict-mcp-config`,
`--setting-sources ""`, `--disable-slash-commands`, `--no-session-persistence`,
and a working directory inside `$TMPDIR`. It loads no settings and therefore no
hooks, no `CLAUDE.md`, and no MCP servers, and it cannot reach your project.
`SPEAK_ENGLISH_CHILD=1` in its environment is the second lock against recursion.

The buffer holds whole assistant messages, so its root is per-uid, created under
`umask 077`, and verified to be a directory this user owns at mode 700 before
anything is written. A symlink is refused before `chmod` runs, since `chmod`
follows one.

The message being rewritten is wrapped in a tag whose nonce is derived from the
message's own SHA-1. A fixed tag would be an escape hatch, because a message
quoting untrusted text could carry the closing tag and address the rewriter as
itself. A message cannot contain its own digest, and the hook skips the rewrite
outright if one ever does.

The rewriter has no tools, so the worst case of a successful injection is a
misleading rewrite on screen. The original stays in the transcript, and the
guards still hold: injected text cannot change a code block, or put an invented
command or path on screen, without the rewrite being thrown away.

## Checking it works

```bash
./hooks/selftest.sh
SPEAK_ENGLISH_MODE=append ./hooks/selftest.sh
SPEAK_ENGLISH_MODEL=not-a-real-model ./hooks/selftest.sh   # fail-open path
SPEAK_ENGLISH_STYLE_FILE=/nonexistent ./hooks/selftest.sh  # fail-open path
```

The self-test feeds the hook a synthetic two-flush message and prints what the
screen would show. It makes one real headless call, and it forces the switch on
for its own run.

## Requirements

`claude` and `jq` on `PATH`, and bash. Tested on macOS with bash 3.2 and with
GNU coreutils first on `PATH`.

## License

MIT. See [LICENSE](LICENSE).
