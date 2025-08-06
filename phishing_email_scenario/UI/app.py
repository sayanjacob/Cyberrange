from flask import Flask, render_template, request, redirect
import subprocess

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    subprocess.Popen(["vagrant", "up"], cwd="phishing_email_scenario")
    return redirect("/")

@app.route("/stop")
def stop():
    subprocess.Popen(["vagrant", "halt"], cwd="phishing_email_scenario")
    return redirect("/")

@app.route("/guide")
def guide():
    with open("phishing_email_scenario/README.md", "r") as f:
        content = f.read()
    return f"<pre>{content}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
