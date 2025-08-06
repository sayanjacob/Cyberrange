from flask import Flask, render_template, request, redirect
import subprocess
import os
import threading

app = Flask(__name__)

# Get base path: phishing_email_scenario/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Lock to prevent concurrent 'vagrant up'
vagrant_lock = threading.Lock()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    if not vagrant_lock.acquire(blocking=False):
        return "<pre>Vagrant is already starting. Please wait...</pre>", 429

    try:
        subprocess.Popen(["vagrant", "up"], cwd=BASE_DIR)
        return redirect("/")
    finally:
        vagrant_lock.release()

@app.route("/stop")
def stop():
    subprocess.Popen(["vagrant", "halt"], cwd=BASE_DIR)
    return redirect("/")

@app.route("/guide")
def guide():
    readme_path = os.path.join(BASE_DIR, "README.md")
    if not os.path.exists(readme_path):
        return "<pre>README.md not found.</pre>", 404

    with open(readme_path, "r") as f:
        content = f.read()
    return f"<pre>{content}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
