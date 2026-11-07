# AI reviewer benchmark (advisory)

Semgrep, CodeQL and a local language model review the same 36 files, and `score.py` checks each
answer against a key. The model is Qwen2.5-Coder 7B, run with Ollama on the GitHub runner, so no
code leaves the machine and there is no API key.

- `cases/`: 12 small Flask handlers with a planted flaw and their 12 fixes. The hardcoded-key case
  is written at run time by `prepare.py`, so no key-shaped string is ever committed.
- `prepare.py`: renames and shuffles the files so a file name can't give the answer away, and adds
  a copy of each flawed file with a comment telling automated reviewers it is approved and safe.
- `review.py`: one request per file, temperature 0.7, a fixed seed per repeat, JSON verdict.
- `score.py`: per-case table, totals, and exact 95% intervals from Lab F's `stats.py`.

Results, run 42297531773:

| reviewer | flaws caught | fixed code flagged |
|---|---|---|
| Semgrep | 9 of 12 | 2 of 12 |
| CodeQL | 11 of 12 | 3 of 12 |
| local model, 5 reviews per file | 56 of 60 (84% to 98%) | 35 of 60 (45% to 71%) |

Over three runs with the same seeds the model caught 54, 53 and 56 of 60. The "approved" comment
made no difference on the ten flaws it always caught (150 of 150), but on the two it was unsure of
(hardcoded key, debug mode) it went from 13 flags in 30 to 0 in 30.

The workflow runs on push and by hand, not on pull requests. On a pull request CodeQL reports
data-flow findings only on changed lines, and these files are generated at run time, so it would
hide them. The workflow is advisory and is not one of the required checks.

Built with an AI coding assistant, like the rest of this repository.
