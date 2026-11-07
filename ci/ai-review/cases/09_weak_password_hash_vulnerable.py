import hashlib
from flask import Flask, request

app = Flask(__name__)
USERS = {}


@app.route("/register", methods=["POST"])
def register():
    user, password = request.form["user"], request.form["password"]
    USERS[user] = hashlib.md5(password.encode()).hexdigest()
    return "ok"
