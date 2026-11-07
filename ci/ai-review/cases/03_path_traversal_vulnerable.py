import os
from flask import Flask, request

app = Flask(__name__)
MAPS = "/srv/maps"


@app.route("/map")
def get_map():
    name = request.args.get("name", "")
    with open(os.path.join(MAPS, name), "rb") as f:
        return f.read()
