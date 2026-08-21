"""Count the style guide's own tells in each arm of evals/results.json.

Regex, not a model, so the number is reproducible and arguable. Fenced code is
excluded, because the guide requires it to survive unchanged and counting it
would reward a rewriter for deleting it.

    python3 evals/score.py evals/results.json
    python3 evals/score.py evals/results.json --markdown > evals/RESULTS.md
"""
import re, sys, json

TELLS = {
  "praise-opener": r"(?im)^(you're absolutely right|you're right|great question|excellent point|good catch|great catch|absolutely)\b",
  "filler-opener": r"(?i)\b(it'?s worth noting|i should mention|in essence|essentially|fundamentally|at its core|simply put)\b",
  "narration": r"(?im)^\s*(let me\b|i'?ll go ahead|now let'?s\b)",
  "inflated-vocab": r"(?i)\b(delve|leverag(e|es|ing)|utiliz(e|es|ing)|facilitat(e|es)|robust|seamless(ly)?|comprehensive|crucial|pivotal|vital|streamlin(e|es|ing)|holistic|nuanced|intricate|elevat(e|es)|unlock(s|ing)?|harness(es|ing)?|meticulous|testament|landscape|realm|tapestry)\b",
  "transition-scaffold": r"(?i)\b(furthermore|moreover|additionally|in conclusion|overall|that said|importantly|notably)\b",
  "contrast-tic": r"(?i)(it'?s not just [^.,;]{1,40}[,.] it'?s|this isn'?t [^.,;]{1,40}\.\s*it'?s|isn'?t the problem[.,]\s*\w+ is)",
  "em-dash": r"—",
  "hedge-stack": r"(?i)\b(may potentially|could possibly|generally tends to|might potentially)\b",
  "inline-bold": r"(?<!^)\*\*[^*\n]{1,60}\*\*",
  "headings": r"(?m)^#{1,6}\s",
}

def score(text):
    # exclude fenced code from tell counting
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    return {k: len(re.findall(p, prose)) for k, p in TELLS.items()}



def tally(arms):
    """Per-arm tell counts and total characters."""
    totals = {n: {k: 0 for k in TELLS} for n in arms}
    chars = {n: 0 for n in arms}
    for n, outs in arms.items():
        for out in outs:
            for k, v in score(out).items():
                totals[n][k] += v
            chars[n] += len(out)
    return totals, chars


def plain(names, totals, chars):
    w = max(len(k) for k in TELLS) + 2
    c = max(len(n) for n in names) + 3
    rows = [f"{'tell':{w}}" + "".join(f"{n:>{c}}" for n in names)]
    for k in TELLS:
        rows.append(f"{k:{w}}" + "".join(f"{totals[n][k]:>{c}}" for n in names))
    rows.append(f"{'TOTAL tells':{w}}" + "".join(f"{sum(totals[n].values()):>{c}}" for n in names))
    rows.append(f"{'total chars':{w}}" + "".join(f"{chars[n]:>{c}}" for n in names))
    return "\n".join(rows)


def markdown(data, names, totals, chars):
    arms = data["arms"]
    n_prompts = len(data["prompts"])
    out = []
    out.append("# Eval results")
    out.append("")
    out.append(f"{n_prompts} prompts, model `{data.get('model', 'sonnet')}`, "
               f"one-shot `claude -p`. Regenerate with:")
    out.append("")
    out.append("```bash")
    out.append("python3 evals/run.py")
    out.append("python3 evals/score.py evals/results.json --markdown > evals/RESULTS.md")
    out.append("```")
    out.append("")
    out.append("Tells are counted by regex over the prose. Fenced code is excluded, because")
    out.append("the guide requires it to survive unchanged and counting it would reward a")
    out.append("rewriter for deleting it. Lower is better in every column.")
    out.append("")

    head = "| tell | " + " | ".join(f"`{n}`" for n in names) + " |"
    sep = "| --- | " + " | ".join("---:" for _ in names) + " |"
    out += [head, sep]
    for k in TELLS:
        row = [str(totals[n][k]) for n in names]
        if all(v == "0" for v in row):
            continue  # a tell nothing produced says nothing
        out.append(f"| {k} | " + " | ".join(row) + " |")
    out.append("| **total tells** | " + " | ".join(f"**{sum(totals[n].values())}**" for n in names) + " |")
    out.append("| total characters | " + " | ".join(f"{chars[n]:,}" for n in names) + " |")
    out.append("")
    zero = [k for k in TELLS if all(totals[n][k] == 0 for n in names)]
    if zero:
        out.append("Never produced by any arm, so the run does not test them: "
                   + ", ".join(f"`{k}`" for k in zero) + ". These are the tells that show")
        out.append("up after twenty turns of real work, not in a one-shot answer, so the totals")
        out.append("above understate what the rewriter has to remove in a session.")
        out.append("")

    out.append("## Per prompt")
    out.append("")
    out.append("Characters, so the length effect is visible per question rather than only in")
    out.append("the total.")
    out.append("")
    out.append("| prompt | " + " | ".join(f"`{n}`" for n in names) + " |")
    out.append("| --- | " + " | ".join("---:" for _ in names) + " |")
    for i, p in enumerate(data["prompts"]):
        label = p if len(p) <= 58 else p[:57] + "…"
        out.append(f"| {label} | " + " | ".join(f"{len(arms[n][i]):,}" for n in names) + " |")
    out.append("")

    out.append("## One answer, every arm")
    out.append("")
    pick = min(range(len(data["prompts"])), key=lambda i: len(arms[names[0]][i]))
    out.append(f"Prompt: **{data['prompts'][pick]}**")
    out.append("")
    for n in names:
        text = arms[n][pick]
        out.append(f"### `{n}` ({len(text):,} characters)")
        out.append("")
        out.append("> " + text.replace("\n", "\n> "))
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    path = sys.argv[1]
    data = json.load(open(path))
    names = list(data["arms"])
    totals, chars = tally(data["arms"])
    if "--markdown" in sys.argv:
        print(markdown(data, names, totals, chars))
    else:
        print(plain(names, totals, chars))
