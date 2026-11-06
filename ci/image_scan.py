#!/usr/bin/env python3
"""Redaction check for published images (part of Gate 1; canary in Gate 0).

Screenshots are the one place a secret scanner never looks: gitleaks reads text,
and an ID inside a PNG is pixels. This runs OCR over every image in the working
tree that is published, and fails if it reads anything identifier-shaped:

  * evidence/screens/*.png
  * every image embedded in docs/index.html (the public GitHub Pages site)

It scans the current tree, not history. History is deliberately left intact;
see finding 4 in audit/CIP-010-R1-evidence.md.

usage:  python3 ci/image_scan.py [image-or-html ...]     exit 1 on any finding
"""
import base64, io, os, re, sys, glob, unicodedata
# One tesseract thread per worker: OpenMP threads inside a process pool oversubscribe the CPU
# and made this step take 15+ minutes on a CI runner.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageOps
import pytesseract

# OCR misreads hex in monospace screenshots (7 -> "/", 1 -> "l", 0 -> "O", "Q" or "@"), so the GUID
# pattern accepts those look-alikes and normalises them; a strict [0-9a-f] pattern
# missed real GUIDs in testing. Found by the Gate 0 canary on its first run.
H = r"[0-9a-fA-F/lIi|oOQ@sSzZ*]"
CONFUSABLE = str.maketrans({"*": "f", "/": "7", "l": "1", "I": "1", "i": "1", "|": "1", "o": "0", "O": "0", "Q": "0", "@": "0", "s": "5", "S": "5", "z": "2", "Z": "2"})
PATTERNS = {
    "guid":         rf"(?<![0-9A-Za-z]){H}{{7,10}}-{H}{{3,5}}-{H}{{3,5}}(?:-{H}{{3,5}}(?:-{H}{{6,13}})?)?",
    "public-ipv4":  r"\b(?!10\.|127\.|0\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "email":        r"(?<![\w*.+-])[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9-]+\.[A-Za-z.]{2,}",
    "key-material": r"(AccountKey=|SharedAccessSignature=|[?&]sig=|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,})",
}
# Strings that are public by design. Each one is explained; nothing is allowed silently.
ALLOW = {
    "noreply@anthropic.com",   # Co-Authored-By trailer, public on every commit
    "noreply@github.com",
}


def images_from(path):
    if path.endswith(".html"):
        html = open(path, encoding="utf-8").read()
        for i, (alt, b64) in enumerate(re.findall(r'<img alt="([^"]*)"[^>]*?src="data:image/\w+;base64,([^"]+)"', html)):
            yield f"{path}#img{i:02d} ({alt[:50]})", Image.open(io.BytesIO(base64.b64decode(b64)))
    else:
        yield path, Image.open(path)


def ocr(img):
    img = img.convert("L")
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    text = pytesseract.image_to_string(img, config="--psm 6")
    text += "\n" + pytesseract.image_to_string(ImageOps.invert(img), config="--psm 6")
    return text


def repair(text):
    """Undo the OCR errors measured on 120 rendered GUIDs (18% were missed before this):
    a 7 read as "/7" and a 1 read as "1l" (one character becomes two), and a space slipped in
    beside a hyphen. The GUID pattern also allows each group to be one character long or short.

    Added 6 Nov 2026 after ci/measure_redaction.py missed 2 of 300: OCR inserted an accented
    letter ("b6ébe/982"), so accents are stripped first, and it read an f as "*", which is now a
    look-alike for f."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"/(?=7)", "", text)
    text = re.sub(r"1l|l1", "1", text)
    text = re.sub(r"(?<=[0-9A-Za-z])[ \t]+-|-[ \t]+(?=[0-9A-Za-z])", "-", text)
    return text


def scan_one(item):
    name, img = item
    return name, find(repair(ocr(img)))


def find(text):
    """Identifier-shaped strings in OCR text. Split out so ci/measure_redaction.py can score
    the same logic with and without repair()."""
    hits = []
    for kind, pat in PATTERNS.items():
        for m in re.finditer(pat, text, re.I):
            v = m.group(0)
            if kind == "guid":
                v = v.translate(CONFUSABLE).lower()
                if not re.fullmatch(r"[0-9a-f]{7,10}-[0-9a-f]{3,5}-[0-9a-f]{3,5}.*", v) or not re.search(r"\d", v):
                    continue
            if v.lower() in ALLOW:
                continue
            hits.append((kind, v))
    return sorted(set(hits))


def main(args):
    targets = args or sorted(glob.glob("evidence/screens/*.png")) + (["docs/index.html"] if glob.os.path.exists("docs/index.html") else [])
    items = [it for t in targets for it in images_from(t)]
    with ProcessPoolExecutor() as ex:
        results = list(ex.map(scan_one, items))
    bad = [(n, h) for n, h in results if h]
    print(f"image redaction check: {len(items)} images scanned, {len(bad)} with findings")
    for n, hits in bad:
        for kind, v in hits:
            print(f"  FINDING  {n}: {kind}: {v}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
