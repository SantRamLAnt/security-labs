#!/usr/bin/env python3
"""Gate 0 canary for the image redaction check: render a fresh random GUID into a
terminal-style screenshot at run time and require ci/image_scan.py to flag a GUID in it.
Flagging is the test, not reproducing every digit: OCR can garble a digit and the
screenshot still must not ship. Never committed, never a real identifier."""
import sys, uuid, subprocess, tempfile, os
from PIL import Image, ImageDraw, ImageFont
g = str(uuid.uuid4())
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)
im = Image.new("RGB", (1100, 90), (12, 12, 12)); d = ImageDraw.Draw(im)
d.text((10, 12), "$ az ad sp show --id <canary>", fill=(200, 200, 200), font=font)
d.text((10, 44), f"(AuthorizationFailed) The client '{g}' does not have authorization", fill=(230, 80, 80), font=font)
p = os.path.join(tempfile.mkdtemp(), "canary.png"); im.save(p)
rc = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "image_scan.py"), p], capture_output=True, text=True)
print(rc.stdout.strip())
if rc.returncode == 0 or ": guid: " not in rc.stdout:
    print(f"::error::image redaction check did NOT catch the canary GUID. Gate 1 image scan cannot be trusted."); sys.exit(1)
print("canary GUID detected: the image redaction check is evaluating")
