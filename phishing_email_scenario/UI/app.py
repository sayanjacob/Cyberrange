from flask import Flask, render_template, request, redirect
import subprocess
import os

app = Flask(__name__)
scenario_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    subprocess.Popen(["vagrant", "up"], cwd=scenario_path)
    return redirect("/")

@app.route("/stop")
def stop():
    subprocess.Popen(["vagrant", "halt"], cwd=scenario_path)
    return redirect("/")

@app.route("/guide")
def guide():
    with open("phishing_email_scenario/README.md", "r") as f:
        content = f.read()
    return f"<pre>{content}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
