import yaml
from flask import Flask, request

app = Flask(__name__)


@app.route("/settings", methods=["POST"])
def settings():
    config = yaml.safe_load(request.data)
    return {"keys": list(config)}
