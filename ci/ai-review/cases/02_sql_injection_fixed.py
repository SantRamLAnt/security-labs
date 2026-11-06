import sqlite3
from flask import Flask, request

app = Flask(__name__)


@app.route("/valve")
def valve():
    valve_id = request.args.get("id", "")
    db = sqlite3.connect("assets.db")
    rows = db.execute("SELECT status FROM valves WHERE id = ?", (valve_id,)).fetchall()
    return {"rows": rows}
