# Eval results

8 prompts, model `sonnet`, one-shot `claude -p`. Regenerate with:

```bash
python3 evals/run.py
python3 evals/score.py evals/results.json --markdown > evals/RESULTS.md
```

Tells are counted by regex over the prose. Fenced code is excluded, because
the guide requires it to survive unchanged and counting it would reward a
rewriter for deleting it. Lower is better in every column.

| tell | `no-guide` | `guide-injected` | `injected-then-rewritten` | `rewriter-only` |
| --- | ---: | ---: | ---: | ---: |
| transition-scaffold | 1 | 0 | 0 | 1 |
| em-dash | 36 | 9 | 1 | 2 |
| inline-bold | 41 | 37 | 32 | 12 |
| headings | 1 | 8 | 8 | 1 |
| **total tells** | **79** | **54** | **41** | **16** |
| total characters | 14,563 | 15,778 | 15,159 | 13,792 |

Never produced by any arm, so the run does not test them: `praise-opener`, `filler-opener`, `narration`, `inflated-vocab`, `contrast-tic`, `hedge-stack`. These are the tells that show
up after twenty turns of real work, not in a one-shot answer, so the totals
above understate what the rewriter has to remove in a session.

## Per prompt

Characters, so the length effect is visible per question rather than only in
the total.

| prompt | `no-guide` | `guide-injected` | `injected-then-rewritten` | `rewriter-only` |
| --- | ---: | ---: | ---: | ---: |
| Why does my React component re-render every time the pare… | 1,453 | 1,234 | 1,159 | 1,289 |
| Explain database connection pooling. | 2,552 | 3,215 | 3,215 | 2,463 |
| How do I fix a memory leak in a long-running Node.js proc… | 2,661 | 2,219 | 2,154 | 2,562 |
| Why am I getting CORS errors in my browser console? | 1,994 | 2,210 | 2,046 | 1,829 |
| How does git rebase differ from git merge? | 1,133 | 1,410 | 1,410 | 1,035 |
| When should I use a queue vs a topic in messaging systems? | 1,481 | 1,558 | 1,489 | 1,356 |
| Our Postgres migration hangs in production. Where do I st… | 2,572 | 2,699 | 2,540 | 2,572 |
| Is it worth adding a feature flag for a small backend beh… | 717 | 1,233 | 1,146 | 686 |

## One answer, every arm

Prompt: **Is it worth adding a feature flag for a small backend behaviour change?**

### `no-guide` (717 characters)

> Not usually — for a small backend behavior change, a feature flag adds ongoing complexity (extra code paths, cleanup work later) that's rarely worth it unless one of these applies:
> 
> - The change is risky enough that you'd want a fast kill-switch without a redeploy
> - You need gradual rollout (canary %, specific users/orgs) rather than all-or-nothing
> - It's tied to a coordinated launch (frontend/backend rollout, marketing timing)
> 
> If none of those hold, just ship it behind normal code review + tests, and roll back via git/deploy if it breaks. A flag you add "just in case" tends to become permanent dead code nobody removes.
> 
> If you tell me what the behavior change actually is, I can give a more concrete yes/no.

### `guide-injected` (1,233 characters)

> Usually not. A feature flag earns its cost when at least one of these is true:
> 
> - The change is risky in production and you want a fast kill switch without a redeploy.
> - You need to roll it out gradually (percentage, cohort, region) rather than all at once.
> - You need to run old and new behavior side by side, for A/B testing or migration.
> - Rollback via redeploy or revert is slow or blocked (e.g., infrequent release cadence, manual approval gates).
> 
> If none of those apply, skip the flag. For a small, low-risk change, a normal PR with tests and a quick revert path is cheaper and clearer. Reasons to skip:
> 
> - Flags accumulate. Someone has to remember to remove them, and stale flags become dead code paths and untested branches.
> - Every flag doubles the states you need to reason about and test (on and off).
> - A revert commit is often faster to ship than the flag infrastructure itself, if your deploy pipeline is fast.
> 
> Rule of thumb: if you can redeploy in minutes and the blast radius is small, just ship it and revert if it breaks. Reach for a flag when the blast radius is large, the rollout needs to be gradual, or rollback by deploy is too slow.
> 
> If you want, tell me the specific change and I'll give a concrete yes/no.

### `injected-then-rewritten` (1,146 characters)

> A feature flag earns its cost only when at least one of these applies:
> 
> - The change is risky in production and needs a fast kill switch without a redeploy.
> - The rollout needs to be gradual (percentage, cohort, region) rather than all at once.
> - Old and new behavior need to run side by side, for A/B testing or migration.
> - Rollback by redeploy or revert is slow or blocked (infrequent release cadence, manual approval gates).
> 
> If none apply, skip the flag. For a small, low-risk change, a normal PR with tests and a quick revert path is cheaper and clearer, because:
> 
> - Flags accumulate. Someone has to remember to remove them, and stale flags become dead code paths and untested branches.
> - Each flag doubles the states you need to test (on and off).
> - A revert commit often ships faster than the flag infrastructure itself, if the deploy pipeline is fast.
> 
> Rule of thumb: if you can redeploy in minutes and the blast radius is small, ship it and revert if it breaks. Reach for a flag when the blast radius is large, the rollout must be gradual, or rollback by deploy is too slow.
> 
> Tell me the specific change and I'll give a concrete yes/no.

### `rewriter-only` (686 characters)

> Usually not. For a small backend behavior change, a feature flag adds ongoing complexity (extra code paths, cleanup work later) that's rarely worth it unless one of these applies:
> 
> - The change is risky enough to need a kill switch without a redeploy.
> - You need gradual rollout (canary percentage, specific users or orgs) instead of all-or-nothing.
> - It's tied to a coordinated launch (frontend/backend rollout, marketing timing).
> 
> If none apply, ship it behind normal code review and tests, and roll back via git/deploy if it breaks. A flag added "just in case" tends to become permanent dead code nobody removes.
> 
> Tell me what the behavior change is and I can give a concrete yes/no.

