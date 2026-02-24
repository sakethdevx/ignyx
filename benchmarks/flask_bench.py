from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def hello():
    return jsonify(message="Hello, World!")

@app.get("/plaintext")
def plaintext():
    return "Hello, World!"
