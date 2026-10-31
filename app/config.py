"""
LAB E - configuration, after remediation.

The synthetic GRIDOPS_API_KEY committed in 508b684 has been removed. Because it is
still in git history, Gate 1 keeps failing until the finding is formally dispositioned:
in a real incident that means ROTATE the credential first, then either rewrite history
or record the historical finding as accepted. This key was synthetic (it unlocks
nothing), so it is recorded in .gitleaksignore with the reason.

Secrets now come from the environment, never from source.
"""
import os

GRIDOPS_API_KEY = os.environ.get("GRIDOPS_API_KEY")  # injected at runtime; never committed

DB_HOST = "localhost"
DB_PORT = 5432
