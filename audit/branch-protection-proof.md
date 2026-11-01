# Branch protection proof — 1 Nov 2026

Verbatim terminal output. PR #1 deliberately re-enabled public blob access; Gate 2 failed it.
Before protection, GitHub offered a working Merge button (evidence/screens/pr1-before-protection-mergeable.png).
After protection, the same merge was refused:

```
PR #1 mergeable_state: behind
$ gh api -X PUT repos/SantRamLAnt/security-labs/pulls/1/merge
{"message":"5 of 5 required status checks are expected.","documentation_url":"https://docs.github.com/articles/about-protected-branches","status":"405"}gh: 5 of 5 required status checks are expected. (HTTP 405)
```

PR #1 was then closed without merging. PR #2 (all five gates passing) merged through the same protected path as `5d6a986`.
