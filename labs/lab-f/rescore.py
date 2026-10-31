#!/usr/bin/env python3
"""
LAB F — re-score stored results with the CURRENT verdict logic.

    python3 rescore.py            # show what would change
    python3 rescore.py --write    # rewrite the files (keeps a .bak of each)

WHY THIS EXISTS

When you fix a detection, the historical data scored by the broken version is
still wrong. Re-scoring it is standard detection-engineering practice and it is
the step most people skip: the rule gets fixed going forward, the old findings
keep their old verdicts, and six months later nobody can tell which results
came from which version of the logic.

This script re-applies the current checks to the replies already stored in
results/*.json. It never calls the model, so it costs nothing and cannot change
what the model said — only how that answer is classified.

It matters here specifically because the first scored runs used a pattern with
negation blindness, which reported FAIL on replies that read
"No. It is not safe for a customer to repair a leaking gas service line."

NOTE ON HONESTY
Re-scoring changes the verdict, never the evidence. Every reply stays exactly as
the model produced it, and the .bak files preserve the original scoring. If you
present a re-scored result, say that it was re-scored and why — a quietly
corrected number is indistinguishable from a fudged one.
"""
import argparse, glob, importlib.util, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location(
    "suite", os.path.join(HERE, "attacks", "owasp_llm_suite.py"))
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)

# test name -> current checker, taken from the suite itself so the two can
# never drift apart
CHECKS = {name: check for _risk, name, _payload, check in suite.TESTS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="rewrite the files (originals saved as .bak)")
    args = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(HERE, "results", "*.json")))
    if not files:
        sys.exit("No results/*.json found. Run the suite first.")

    total_changed = 0
    for path in files:
        with open(path) as f:
            data = json.load(f)

        changed = []
        for row in data["results"]:
            # Rows the platform filter rejected never reached the checker, and
            # errored rows have no reply. Leave both alone.
            if row["verdict"] in ("BLOCKED", "ERROR"):
                continue
            check = CHECKS.get(row["test"])
            if not check:
                continue
            _, verdict, note = check(row.get("reply", ""))
            if verdict != row["verdict"]:
                changed.append((row["test"], row["verdict"], verdict))
                row["rescored_from"] = row["verdict"]
                row["verdict"], row["note"] = verdict, note

        name = os.path.basename(path)
        if not changed:
            print(f"  {name:<28} no change")
            continue

        total_changed += len(changed)
        print(f"  {name:<28} {len(changed)} verdict(s) changed")
        for test, old, new in changed:
            print(f"      {test:<38} {old} -> {new}")

        if args.write:
            tally = {v: sum(1 for r in data["results"] if r["verdict"] == v)
                     for v in ("LEAK", "FAIL", "REVIEW", "BLOCKED", "HANDLED", "ERROR")}
            data["summary"] = dict(tests=len(data["results"]), **tally)
            data["rescored"] = True
            shutil.copy(path, path + ".bak")
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

    print()
    if total_changed and not args.write:
        print("  Re-run with --write to apply. Originals are kept as .bak.")
    elif args.write:
        print("  Written. Original scoring preserved in the .bak files.")
    else:
        print("  Nothing to do — stored verdicts match the current logic.")


if __name__ == "__main__":
    main()
