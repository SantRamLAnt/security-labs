import hashlib
import os
from flask import Flask, request

app = Flask(__name__)
USERS = {}


@app.route("/register", methods=["POST"])
def register():
    user, password = request.form["user"], request.form["password"]
    salt = os.urandom(16)
    USERS[user] = (salt, hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1))
    return "ok"
