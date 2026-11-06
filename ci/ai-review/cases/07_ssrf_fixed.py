from urllib.parse import urlparse

import requests
from flask import Flask, abort, request

app = Flask(__name__)
ALLOWED = {"tiles.example.org"}


@app.route("/fetch")
def fetch():
    url = request.args.get("url", "")
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED:
        abort(400)
    return requests.get(url, timeout=5).text
