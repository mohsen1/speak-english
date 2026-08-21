"""Count the style guide's own tells in each arm of evals/results.json.

Regex, not a model, so the number is reproducible and arguable. Fenced code is
excluded, because the guide requires it to survive unchanged and counting it
would reward a rewriter for deleting it.

    python3 evals/score.py evals/results.json
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

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    arms = data["arms"]
    names = list(arms)
    totals = {n: {k: 0 for k in TELLS} for n in names}
    chars = {n: 0 for n in names}
    for n in names:
        for out in arms[n]:
            for k, v in score(out).items():
                totals[n][k] += v
            chars[n] += len(out)
    keys = list(TELLS)
    w = max(len(k) for k in keys) + 2
    c = max(len(n) for n in names) + 3
    print(f"{'tell':{w}}" + "".join(f"{n:>{c}}" for n in names))
    for k in keys:
        print(f"{k:{w}}" + "".join(f"{totals[n][k]:>{c}}" for n in names))
    print(f"{'TOTAL tells':{w}}" + "".join(f"{sum(totals[n].values()):>{c}}" for n in names))
    print(f"{'total chars':{w}}" + "".join(f"{chars[n]:>{c}}" for n in names))
