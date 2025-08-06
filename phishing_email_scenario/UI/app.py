from flask import Flask, render_template, request, redirect, Response
import subprocess
import os
import threading
import time

app = Flask(__name__)

# Base directory: phishing_email_scenario/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_FILE = os.path.join(BASE_DIR, "vagrant.log")

# Lock to prevent concurrent 'vagrant up' calls
vagrant_lock = threading.Lock()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
def start():
    if not vagrant_lock.acquire(blocking=False):
        return "<pre>Vagrant is already starting. Please wait...</pre>", 429

    try:
        # Clear previous logs
        with open(LOG_FILE, "w") as log_file:
            # Start vagrant up and pipe logs to file
            subprocess.Popen(
                ["vagrant", "up"],
                cwd=BASE_DIR,
                stdout=log_file,
                stderr=log_file
            )
        return redirect("/")
    finally:
        vagrant_lock.release()

@app.route("/stop")
def stop():
    with open(LOG_FILE, "a") as log_file:
        subprocess.Popen(
            ["vagrant", "halt"],
            cwd=BASE_DIR,
            stdout=log_file,
            stderr=log_file
        )
    return redirect("/")

@app.route("/guide")
def guide():
    readme_path = os.path.join(BASE_DIR, "README.md")
    if not os.path.exists(readme_path):
        return "<pre>README.md not found.</pre>", 404

    with open(readme_path, "r") as f:
        content = f.read()
    return f"<pre>{content}</pre>"

@app.route("/logs")
def stream_logs():
    def generate_logs():
        # Ensure the log file exists
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()

        with open(LOG_FILE, "r") as f:
            f.seek(0, os.SEEK_END)  # Move to the end

            while True:
                line = f.readline()
                if line:
                    print(line.strip())  # Show logs on the server terminal
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(0.5)

    return Response(generate_logs(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
