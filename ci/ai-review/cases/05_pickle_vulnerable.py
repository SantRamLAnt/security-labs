import pickle
from flask import Flask, request

app = Flask(__name__)


@app.route("/import", methods=["POST"])
def import_job():
    job = pickle.loads(request.data)
    return {"segments": len(job["segments"])}
