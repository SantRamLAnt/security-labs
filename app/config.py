"""
LAB E - planted finding.

The credential below is AWS's PUBLISHED EXAMPLE key from their own
documentation. It is not a real credential and never was. It exists so the
secret-scanning gate has something to catch.

Gate 1 should fail on this file. Removing these lines should make it pass.
That before/after is the evidence.
"""

# gitleaks:allow-is-NOT-set-here-on-purpose
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

DB_HOST = "localhost"
DB_PORT = 5432
