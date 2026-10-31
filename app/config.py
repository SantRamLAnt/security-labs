"""
LAB E - planted findings for the secret-scanning gate.

Both values below are FAKE. Neither is, or ever was, a real credential.

1. AWS's published documentation example key. Run #1 showed gitleaks (and trivy's
   secret scanner) deliberately ignore it, so on its own it proves nothing.
2. A random 40-character string generated for this lab on 31 Oct 2026, shaped like
   an API key so the scanner has something real to catch. It unlocks nothing.

Gate 1 must fail while (2) is in the code or the history.
"""

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"          # documentation example: allowlisted by scanners
GRIDOPS_API_KEY = "Vg3Oep8UUfJHRV05MdGwilP4xpgrFpEkuTD3mIZF"   # synthetic, generated for this lab

DB_HOST = "localhost"
DB_PORT = 5432
