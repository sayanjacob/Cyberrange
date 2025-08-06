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

def run_vagrant_command(command):
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(
            command,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        process.wait()

@app.route("/start")
def start():
    if not vagrant_lock.acquire(blocking=False):
        return "<pre>Vagrant is already starting. Please wait...</pre>", 429

    try:
        threading.Thread(target=run_vagrant_command, args=(["vagrant", "up"],), daemon=True).start()
        return redirect("/")
    finally:
        vagrant_lock.release()

@app.route("/stop")
def stop():
    threading.Thread(target=run_vagrant_command, args=(["vagrant", "halt"],), daemon=True).start()
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
