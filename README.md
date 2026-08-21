# speak-english

A Claude Code plugin that rewrites each finished assistant message into plain
English before it reaches your screen.

A real answer, to "Is it worth adding a feature flag for a small backend
behaviour change?". Before:

> Not usually — for a small backend behavior change, a feature flag adds ongoing
> complexity (extra code paths, cleanup work later) that's rarely worth it unless
> one of these applies:
>
> - The change is risky enough that you'd want a fast kill-switch without a redeploy
> - You need gradual rollout (canary %, specific users/orgs) rather than all-or-nothing
> - It's tied to a coordinated launch (frontend/backend rollout, marketing timing)
>
> If none of those hold, just ship it behind normal code review + tests, and roll
> back via git/deploy if it breaks. A flag you add "just in case" tends to become
> permanent dead code nobody removes.
>
> If you tell me what the behavior change actually is, I can give a more concrete
> yes/no.

After:

> Usually not. For a small backend behavior change, a feature flag adds ongoing
> complexity (extra code paths, cleanup work later) that's rarely worth it unless
> one of these applies:
>
> - The change is risky enough to need a kill switch without a redeploy.
> - You need gradual rollout (canary percentage, specific users or orgs) instead
>   of all-or-nothing.
> - It's tied to a coordinated launch (frontend/backend rollout, marketing timing).
>
> If none apply, ship it behind normal code review and tests, and roll back via
> git/deploy if it breaks. A flag added "just in case" tends to become permanent
> dead code nobody removes.
>
> Tell me what the behavior change is and I can give a concrete yes/no.

The rewriter is Claude Code itself, run headless (`claude -p`) against the login
you already have. No API key, no local model server, no third-party provider.

Only your screen changes. The transcript, the conversation the model sees, and
every other consumer keep the original text.

## Install

```
/plugin marketplace add mohsen1/speak-english
/plugin install speak-english
/speak-english on
```

Installing does nothing on its own. The hook exits until `/speak-english on`.

## Commands

```
/speak-english on        # rewrite from the next message
/speak-english off       # stop
/speak-english append    # keep the original, put the rewrite under it
/speak-english replace   # show the rewrite instead of the original (default)
/speak-english status
```

State is `~/.claude/speak-english-on` and `~/.claude/speak-english-mode`, read
once per message on its first flush. A change applies from the next message. A
message already streaming finishes under the setting it started with.

## Your own style guide

The rewriter follows the first of these that exists:

1. `SPEAK_ENGLISH_STYLE_FILE`
2. `.claude/speak-english-style.md` in the project
3. [`style/plain-english.md`](style/plain-english.md), shipped with the plugin

A project guide replaces the default outright. It is a style guide and nothing
more: the editor contract lives in the hook, which tells the rewriter it is an
editor and not an author, that it may not answer the question, and that it may
not add or remove a fact.

The default guide takes its tells from
[claudish-to-english](https://github.com/gvzdv/claudish-to-english) and its
sentence rules from ASD-STE100 Simplified Technical English.

## How it works

`MessageDisplay` fires once per flush of completed lines while a message
streams. Each fire is a separate process, so every delta is buffered under
`$TMPDIR` and the rewrite happens once, on the final flush.

```
flush 0..n-1  ──▶  delta buffered under $TMPDIR    (replace mode: screen blanked)
flush n       ──▶  reassemble ──▶ claude -p ──▶ guards ──▶ screen
                                                  │
                                                  └── any guard fails ──▶ original
```

It fails open. A missing `jq` or `claude`, an unreadable guide, a timeout, or an
empty rewrite leaves the original on screen, and in `replace` mode that means
the whole message, not just the last delta.

Four guards throw away a rewrite that came back:

- more than twice the length of the original;
- a fenced code block differs by a byte, fence lines included;
- an inline `` `...` `` span from the original is missing;
- a span appears whose text is nowhere in the original.

Spans are compared by text, not markup, so promoting a command from bold to code
passes. Dropping one does not.

Skipped without a rewrite: messages under 200 characters of prose, over 16,000
characters, or that parse as JSON.

## Why a rewriter and not an instruction

Handing the model the guide up front was built and measured over 8 dev questions
on sonnet, counting the guide's own tells by regex:

| Arm                     | Tells | Characters |
| ----------------------- | ----: | ---------: |
| no guide                |    79 |     14,563 |
| guide injected up front |    54 |     15,778 |
| injected and rewritten  |    41 |     15,159 |
| rewriter only, ships    |    16 |     13,792 |

An instruction removes the words it names and nothing else. Every variant tried
made the answer longer and reached for more structure: injecting the guide took
headings from 1 to 8. Rewriting is the only arm that cut length, because an
editor with no task can only delete. Read it as directional, not proof.

## What nothing checks

The prose. The contract forbids adding or removing information and says so
twice, and the rewriter does both anyway. On the self-test message it supplied a
reason the message did not give, in 1 of 3 runs. On an answer comparing `git
merge` and `git rebase` it shortened a markdown table cell from "May need to
resolve conflicts repeatedly, once per replayed commit" to "once per replayed
commit", losing the word that carried the point. Tables are not fenced code, so
no guard looks at them.

So a rewrite that passes all four guards but adds a claim, or softens a caveat,
is what you read. `/speak-english append` keeps both on screen.

## Cost

One headless call per qualifying message, billed to the same subscription as the
session. On an 830-character message, `sonnet` takes 3-6s and about $0.015. In
`replace` mode that time is dead air.

`haiku` is not the cheap option: 80-90s and about $0.044, because it spends
8,000+ thinking tokens on a rewrite and ignores `--effort low`.

## Safety

The rewriter runs with `--tools ""`, `--strict-mcp-config`,
`--setting-sources ""`, `--disable-slash-commands`, `--no-session-persistence`,
and a working directory inside `$TMPDIR`. It loads no settings and therefore no
hooks, no `CLAUDE.md`, and no MCP servers, and it cannot reach your project.
`SPEAK_ENGLISH_CHILD=1` is the second lock against recursion.

Nothing you type reaches a shell. The command runs nothing inline, and
`toggle.sh` matches its argument against the five words and rejects anything
else without evaluating it.

The buffer holds whole messages, so its root is per-uid, created under
`umask 077`, and verified to be a directory you own at mode 700 before anything
is written. A symlink is refused before `chmod` runs, since `chmod` follows one.

The message is wrapped in a tag whose nonce comes from its own SHA-1, so text it
quotes cannot close the tag and address the rewriter. The rewriter has no tools,
so the worst case of a successful injection is a misleading rewrite on screen,
and the guards still stop it changing code or inventing a command.

## Configuration

| Variable                   | Default                        | Meaning                              |
| -------------------------- | ------------------------------ | ------------------------------------ |
| `SPEAK_ENGLISH_ENABLED`    | unset                          | `1` or `0` beats the on-file          |
| `SPEAK_ENGLISH_ON_FILE`    | `~/.claude/speak-english-on`   | Exists means on                      |
| `SPEAK_ENGLISH_STYLE_FILE` | see above                      | The style guide                      |
| `SPEAK_ENGLISH_MODE`       | `replace`                      | `replace` or `append`                |
| `SPEAK_ENGLISH_MODE_FILE`  | `~/.claude/speak-english-mode` | Live mode                            |
| `SPEAK_ENGLISH_MODEL`      | `sonnet`                       | Rewriter model                       |
| `SPEAK_ENGLISH_MIN_CHARS`  | `200`                          | Skip shorter messages, prose only    |
| `SPEAK_ENGLISH_MAX_CHARS`  | `16000`                        | Skip longer messages                 |
| `SPEAK_ENGLISH_TIMEOUT`    | `45`                           | Rewriter timeout, seconds            |
| `SPEAK_ENGLISH_DEBUG`      | `0`                            | Log to the buffer directory          |

Environment variables freeze when the session launches, so they are for scripts.
`/speak-english` is the live switch.

## Development

```bash
./hooks/selftest.sh
SPEAK_ENGLISH_MODE=append ./hooks/selftest.sh
SPEAK_ENGLISH_MODEL=not-a-real-model ./hooks/selftest.sh   # fail-open path
```

The self-test feeds the hook a synthetic two-flush message, prints what the
screen would show, and forces the switch on for its own run. It makes one real
headless call.

Needs `claude` and `jq` on `PATH`, and bash. Tested on macOS with bash 3.2 and
with GNU coreutils first on `PATH`.

## License

MIT
