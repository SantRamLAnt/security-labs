#!/usr/bin/env python3
"""
LAB F - build the before/after comparison from whichever runs exist.

    python3 compare.py

Reads results/naive.json, results/baseline.json, results/guarded.json
(any subset) and writes results/COMPARISON.md.

The comparison across three modes is the artifact worth showing, because it
isolates one variable at a time:

    naive    -> baseline   does INSTRUCTING the model to keep a secret work?
    baseline -> guarded    does REMOVING the secret work better?

A security control is only demonstrated when you can show the result with it
and without it. One run proves nothing either way.
"""
import glob, json, os

ORDER = ["naive", "baseline", "guarded"]
LABEL = {
    "naive":    "Naive (secret in prompt, unprotected)",
    "baseline": "Baseline (secret in prompt, told to protect it)",
    "guarded":  "Guarded (secret not in prompt + output filter)",
}


def load_all():
    """Every results/*.json, ordered naive -> baseline -> guarded, and within
    each mode the untagged run first then tagged variants alphabetically.
    A tag marks a platform-level change (e.g. --tag shields) so the same mode
    can be measured before and after without one overwriting the other."""
    runs = []
    for path in sorted(glob.glob("results/*.json")):
        with open(path) as f:
            d = json.load(f)
        mode = d.get("mode", "?")
        tag = d.get("tag", "")
        key = mode if not tag else f"{mode}+{tag}"
        label = LABEL.get(mode, mode) + (f" — {tag}" if tag else "")
        runs.append({"key": key, "mode": mode, "tag": tag,
                     "label": label, "data": d})
    runs.sort(key=lambda r: (ORDER.index(r["mode"]) if r["mode"] in ORDER else 99,
                             r["tag"]))
    return runs


def main():
    allruns = load_all()
    if not allruns:
        raise SystemExit("No results found. Run the suite first:\n"
                         "  python3 attacks/owasp_llm_suite.py --mode naive")
    runs = [(r["key"], r["data"]) for r in allruns]
    LABEL.update({r["key"]: r["label"] for r in allruns})
    present = [r["key"] for r in allruns]
    rescored = any(r["data"].get("rescored") for r in allruns)
    lines = []
    lines.append("# LAB F — Results")
    lines.append("")
    lines.append(f"Deployment: `{runs[0][1]['deployment']}`  ")
    lines.append(f"Framework: {runs[0][1]['framework']}  ")
    lines.append(f"Runs: {', '.join(present)}")
    if rescored:
        lines.append("")
        lines.append("> Some verdicts were **re-scored** after a fix to the harness "
                     "(negation blindness in the misinformation check). Replies are "
                     "unchanged; original scoring is preserved in the `.bak` files.")
    lines.append("")

    # --- summary table ---
    lines.append("## Summary")
    lines.append("")
    header = "| Configuration | LEAK | FAIL | REVIEW | BLOCKED | HANDLED |"
    lines.append(header)
    lines.append("|---|---|---|---|---|---|")
    for m, d in runs:
        s = d["summary"]
        lines.append(
            f"| {LABEL[m]} | **{s.get('LEAK', 0)}** | {s.get('FAIL', 0)} | "
            f"{s.get('REVIEW', 0)} | {s.get('BLOCKED', 0)} | {s.get('HANDLED', 0)} |")
    lines.append("")

    # --- the deltas that matter ---
    by_mode = dict(runs)
    def hard(m):
        s = by_mode[m]["summary"]
        return s.get("LEAK", 0) + s.get("FAIL", 0)

    def delta(frm, to, label):
        if frm not in by_mode or to not in by_mode:
            return
        a, b = hard(frm), hard(to)
        verdict = ("no change" if a == b
                   else f"{a - b} fewer" if b < a
                   else f"{b - a} more")
        noun = "hard failure" if a == 1 else "hard failures"
        lines.append(f"**{label}:** {a} {noun} (LEAK+FAIL) → {b} — {verdict}.")
        lines.append("")

    delta("naive", "baseline", "Prompt-level defence")
    delta("baseline", "guarded", "Architectural fix")
    delta("naive", "guarded", "Naive to guarded, overall")
    # platform layer: same mode, with and without the tagged change
    for r in allruns:
        if r["tag"]:
            delta(r["mode"], r["key"],
                  f"Platform layer ({r['tag']}) on {r['mode']}")

    # --- per-test matrix ---
    lines.append("## Per-test verdicts")
    lines.append("")
    lines.append("| Risk | Test | " + " | ".join(present) + " |")
    lines.append("|---|---|" + "---|" * len(present))
    for i, t in enumerate(runs[0][1]["results"]):
        cells = []
        for m, d in runs:
            v = d["results"][i]["verdict"]
            cells.append(f"**{v}**" if v in ("LEAK", "FAIL") else v)
        lines.append(f"| {t['risk']} | {t['test']} | " + " | ".join(cells) + " |")
    lines.append("")

    # --- rows a human still has to read ---
    review = [(m, r) for m, d in runs for r in d["results"]
              if r["verdict"] == "REVIEW"]
    if review:
        lines.append("## Rows needing human review")
        lines.append("")
        lines.append("The harness could not judge these. Read them and decide.")
        lines.append("")
        for m, r in review:
            lines.append(f"- **{m} · {r['test']}** — {r['note']}")
        lines.append("")

    # --- evidence of the hard failures ---
    hard_rows = [(m, r) for m, d in runs for r in d["results"]
                 if r["verdict"] in ("LEAK", "FAIL")]
    if hard_rows:
        lines.append("## Hard failures, with evidence")
        lines.append("")
        for m, r in hard_rows:
            lines.append(f"### {m} · {r['risk']} — {r['test']}")
            lines.append(f"*{r['note']}*")
            lines.append("")
            lines.append("```")
            lines.append(r["reply"][:600].strip() or "(no content)")
            lines.append("```")
            lines.append("")
    else:
        lines.append("## No hard failures in any run")
        lines.append("")
        lines.append("Report this plainly rather than reaching for a stronger claim. "
                     "A current small model behind the default content filter "
                     "withstood this attack set, and that is a finding: the 2023-era "
                     "assumption that a naive LLM application trivially surrenders "
                     "its system prompt does not hold for this model.")
        lines.append("")
        lines.append("It is **not** a finding that the application is secure. The "
                     "suite is single-turn, uses published attack shapes a vendor "
                     "has had time to train against, and tests one model on one day. "
                     "Absence of evidence is the correct phrase, and saying so is "
                     "what separates a measurement from a marketing claim.")
        lines.append("")

    os.makedirs("results", exist_ok=True)
    with open("results/COMPARISON.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\nWritten: results/COMPARISON.md")


if __name__ == "__main__":
    main()
