import os

import requests
from flask import Flask

app = Flask(__name__)
API_KEY = os.environ["GRIDOPS_API_KEY"]


@app.route("/feeders")
def feeders():
    r = requests.get("https://gridops.example.org/api/feeders",
                     headers={"Authorization": f"Bearer {API_KEY}"}, timeout=5)
    return r.json()
