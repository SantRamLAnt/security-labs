import yaml
from flask import Flask, request

app = Flask(__name__)


@app.route("/settings", methods=["POST"])
def settings():
    config = yaml.load(request.data, Loader=yaml.Loader)
    return {"keys": list(config)}
