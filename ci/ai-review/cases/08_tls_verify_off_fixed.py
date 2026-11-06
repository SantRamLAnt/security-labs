import requests
from flask import Flask

app = Flask(__name__)


@app.route("/outages")
def outages():
    r = requests.get("https://outages.example.org/api/v1/active", timeout=5)
    return r.json()
