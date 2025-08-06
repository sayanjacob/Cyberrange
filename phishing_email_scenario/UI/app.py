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
        if not os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()

        with open(LOG_FILE, "r") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    print(line.strip())
                    yield f"data: {line.strip()}\n\n"
                else:
                    time.sleep(0.5)
    return Response(generate_logs(), mimetype="text/event-stream")

@app.route("/stream-vagrant-output")
def stream_vagrant_output():
    command = request.args.get("command", "up")  # Default to "up"
    if command not in ["up", "halt"]:
        return Response("Invalid command", mimetype="text/plain")

    def generate_output():
        process = subprocess.Popen(
            ["vagrant", command],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        for line in process.stdout:
            yield f"data: {line.strip()}\n\n"
        process.wait()

    return Response(generate_output(), mimetype="text/event-stream")

@app.route("/vagrant-status")
def vagrant_status():
    try:
        result = subprocess.run(
            ["vagrant", "status"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return Response(result.stdout, mimetype="text/plain")
    except subprocess.CalledProcessError as e:
        return Response(e.stdout, mimetype="text/plain", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
