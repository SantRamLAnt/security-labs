from pathlib import Path
from flask import Flask, abort, request

app = Flask(__name__)
MAPS = Path("/srv/maps").resolve()


@app.route("/map")
def get_map():
    name = request.args.get("name", "")
    path = (MAPS / name).resolve()
    if not path.is_relative_to(MAPS):
        abort(400)
    return path.read_bytes()
