#!/usr/bin/env python3
import os
import sys
import logging
import shlex
import subprocess
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import threading
import time

import requests
from flask import Flask, jsonify, request, Response, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix

# =========================
# Configuration (env vars)
# =========================
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200,*"
).split(",")

SCRIPTS_ROOT = os.path.abspath(
    os.getenv("SCRIPTS_ROOT", os.path.join(os.path.dirname(__file__), "scripts"))
)

# Guacamole base (must point to /guacamole)
GUAC_BASE = os.getenv("GUAC_BASE", "http://20.197.40.109:8080/guacamole")

# Two mapped users (you can switch to env-only by removing defaults)
GUAC_USERS = {
    "victim": {
        "username": os.getenv("GUAC_VICTIM_USER", "victim"),
        "password": os.getenv("GUAC_VICTIM_PASS", "victim"),
        "connection_id": os.getenv("GUAC_VICTIM_CONNECTION", "victim"),
        "display_name": "Victim Machine",
        "description": "Target system for security testing",
        "color_theme": "#3498db",
    },
    "attacker": {
        "username": os.getenv("GUAC_ATTACKER_USER", "attacker"),
        "password": os.getenv("GUAC_ATTACKER_PASS", "attacker"),
        "connection_id": os.getenv("GUAC_ATTACKER_CONNECTION", "Kali_attacker VNC"),
        "display_name": "Attacker Machine",
        "description": "Penetration testing platform",
        "color_theme": "#e74c3c",
    },
}

GUAC_TOKEN_TIMEOUT = int(os.getenv("GUAC_TOKEN_TIMEOUT", "10"))

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
FLASK_USE_RELOADER = os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# =========================
# Scenario command mapping
# =========================
COMMANDS = {
    "phish-101": {
        "start": f"bash {os.path.join(SCRIPTS_ROOT, 'phish-101/start.sh')}",
        "stop": f"bash {os.path.join(SCRIPTS_ROOT, 'phish-101/stop.sh')}",
        "status": f"bash {os.path.join(SCRIPTS_ROOT, 'phish-101/status.sh')}",
        "reset": f"bash {os.path.join(SCRIPTS_ROOT, 'phish-101/reset.sh')}",
        "description": "Email phishing simulation lab",
        "difficulty": "beginner",
        "duration": "30-45 minutes",
    },
    "web-owasp-1": {
        "start": f"bash {os.path.join(SCRIPTS_ROOT, 'web-owasp-1/start.sh')}",
        "stop": f"bash {os.path.join(SCRIPTS_ROOT, 'web-owasp-1/stop.sh')}",
        "status": f"bash {os.path.join(SCRIPTS_ROOT, 'web-owasp-1/status.sh')}",
        "reset": f"bash {os.path.join(SCRIPTS_ROOT, 'web-owasp-1/reset.sh')}",
        "description": "OWASP Top 10 web application vulnerabilities",
        "difficulty": "intermediate",
        "duration": "60-90 minutes",
    },
}


# =========================
# Global state management
# =========================
class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.user_tokens: Dict[str, Dict[str, str]] = (
            {}
        )  # {session_id: {user_type: token}}
        self.connection_status: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_session(self, session_id: str) -> Dict[str, Any]:
        with self.lock:
            session_data = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "active_connections": [],
                "scenario_status": {},
                "user_preferences": {},
            }
            self.active_sessions[session_id] = session_data
            self.user_tokens[session_id] = {}
            return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.active_sessions.get(session_id)

    def update_session_activity(self, session_id: str):
        with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id][
                    "last_activity"
                ] = datetime.now().isoformat()

    def store_user_token(self, session_id: str, user_type: str, token: str):
        with self.lock:
            if session_id not in self.user_tokens:
                self.user_tokens[session_id] = {}
            self.user_tokens[session_id][user_type] = token

    def get_user_token(self, session_id: str, user_type: str) -> Optional[str]:
        with self.lock:
            return self.user_tokens.get(session_id, {}).get(user_type)

    def add_active_connection(self, session_id: str, user_type: str):
        with self.lock:
            if session_id in self.active_sessions:
                connections = self.active_sessions[session_id]["active_connections"]
                if user_type not in connections:
                    connections.append(user_type)

    def remove_active_connection(self, session_id: str, user_type: str):
        with self.lock:
            if session_id in self.active_sessions:
                connections = self.active_sessions[session_id]["active_connections"]
                if user_type in connections:
                    connections.remove(user_type)

    def cleanup_expired_sessions(self):
        with self.lock:
            current_time = datetime.now()
            expired_sessions = []
            for session_id, session_data in self.active_sessions.items():
                last_activity = datetime.fromisoformat(session_data["last_activity"])
                if (current_time - last_activity).seconds > SESSION_TIMEOUT:
                    expired_sessions.append(session_id)
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                if session_id in self.user_tokens:
                    del self.user_tokens[session_id]


session_manager = SessionManager()


# =========================
# Utilities
# =========================
def run_cmd(cmd: str, timeout: int = 90) -> Dict[str, Any]:
    try:
        res = subprocess.run(
            shlex.split(cmd),
            cwd=SCRIPTS_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "success": res.returncode == 0,
            "timestamp": datetime.now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {
            "code": 124,
            "stdout": "",
            "stderr": "Command timed out",
            "success": False,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "code": 1,
            "stdout": "",
            "stderr": f"Exception: {e}",
            "success": False,
            "timestamp": datetime.now().isoformat(),
        }


def get_guac_token(user_type: str) -> Tuple[str, int]:
    if user_type not in GUAC_USERS:
        return f"Invalid user type: {user_type}", 400

    user_config = GUAC_USERS[user_type]
    try:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        payload = {
            "username": user_config["username"],
            "password": user_config["password"],
        }
        response = requests.post(
            f"{GUAC_BASE}/api/tokens",
            data=payload,
            headers=headers,
            timeout=GUAC_TOKEN_TIMEOUT,
            verify=False,
        )
    except requests.exceptions.ConnectTimeout:
        return "Connection timeout to Guacamole server", 504
    except requests.exceptions.ConnectionError as e:
        return f"Cannot connect to Guacamole server: {e}", 502
    except Exception as e:
        return f"Failed to reach Guacamole: {e}", 502

    if response.status_code != 200:
        return (
            f"Guacamole authentication failed for {user_type}: HTTP {response.status_code}: {response.text}",
            502,
        )

    try:
        data = response.json()
    except ValueError as e:
        return f"Invalid JSON response from Guacamole: {e}", 502

    token = data.get("authToken")
    if not token:
        return f"Guacamole did not return an authToken for {user_type}", 500

    return token, 200


def get_guac_connections(token: str) -> Dict[str, Any]:
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(
            f"{GUAC_BASE}/api/session/data/mysql/connections",
            headers=headers,
            params={"token": token},
            timeout=GUAC_TOKEN_TIMEOUT,
            verify=False,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get connections: HTTP {response.status_code}"}
    except Exception as e:
        return {"error": f"Exception getting connections: {e}"}


def tokenized_connection_url(connection_id: str, token: str) -> str:
    """
    Always append ?token=... so Guacamole accepts the session without relying
    on cross-origin storage.
    """
    # Ensure there's no existing query string clash
    sep = "&" if "?" in connection_id else "?"
    return f"{GUAC_BASE}/#/client/{connection_id}?token={token}"


# =========================
# Flask app
# =========================
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = False  # Set True when serving over HTTPS
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=SESSION_TIMEOUT)

    # Reverse proxy headers if behind a proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ---- CORS ----
    CORS(
        app,
        resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # ---- Socket.IO ----
    socketio = SocketIO(
        app,
        cors_allowed_origins=ALLOWED_ORIGINS,
        logger=FLASK_DEBUG,
        engineio_logger=FLASK_DEBUG,
    )

    # ---- Logging ----
    app.logger.setLevel(logging.DEBUG if FLASK_DEBUG else logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if FLASK_DEBUG else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    @app.before_request
    def before_request():
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
            session.permanent = True
            session_manager.create_session(session["session_id"])
        else:
            session_manager.update_session_activity(session["session_id"])

        if FLASK_DEBUG:
            try:
                body = request.get_data(as_text=True) or ""
                body_preview = body[:200] + ("..." if len(body) > 200 else "")
            except Exception:
                body_preview = "<unavailable>"
            app.logger.debug(
                f"[{datetime.now().isoformat()}] {request.remote_addr} "
                f"{request.method} {request.path} "
                f"Session: {session.get('session_id', 'none')[:8]}... "
                f"Body: {body_preview}"
            )

    @app.after_request
    def after_request(response):
        if FLASK_DEBUG:
            app.logger.debug(
                f"[{datetime.now().isoformat()}] -> {response.status} "
                f"for {request.method} {request.path}"
            )
        return response

    # ---- Health and Status ----
    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "session_id": session.get("session_id"),
                "guac_base": GUAC_BASE,
                "active_sessions": len(session_manager.active_sessions),
            }
        )

    @app.get("/api/status")
    def status():
        session_id = session.get("session_id")
        session_data = session_manager.get_session(session_id)
        return jsonify(
            {
                "session": session_data,
                "guac_users": {
                    user_type: {
                        "username": config["username"],
                        "display_name": config["display_name"],
                        "description": config["description"],
                        "color_theme": config["color_theme"],
                        "has_token": session_manager.get_user_token(
                            session_id, user_type
                        )
                        is not None,
                    }
                    for user_type, config in GUAC_USERS.items()
                },
                "scenarios": {
                    sid: {
                        "id": sid,
                        "actions": list(actions.keys()),
                        "description": actions.get("description", ""),
                        "difficulty": actions.get("difficulty", "unknown"),
                        "duration": actions.get("duration", "unknown"),
                    }
                    for sid, actions in COMMANDS.items()
                },
            }
        )

    # ---- Scenarios ----
    @app.get("/api/scenarios")
    def list_scenarios():
        return jsonify(
            {
                "scenarios": [
                    {
                        "id": sid,
                        "actions": [
                            a
                            for a in actions.keys()
                            if not a.startswith(
                                ("description", "difficulty", "duration")
                            )
                        ],
                        "description": actions.get("description", ""),
                        "difficulty": actions.get("difficulty", "unknown"),
                        "duration": actions.get("duration", "unknown"),
                    }
                    for sid, actions in COMMANDS.items()
                ]
            }
        )

    @app.post("/api/scenarios/<sid>/<action>")
    def scenario_action(sid, action):
        session_id = session.get("session_id")
        scenario_map = COMMANDS.get(sid, {})
        cmd = scenario_map.get(action)
        if not cmd:
            return (
                jsonify({"error": f"Unknown scenario '{sid}' or action '{action}'"}),
                404,
            )

        app.logger.info(f"Executing {sid}/{action} for session {session_id}")
        result = run_cmd(cmd)

        session_data = session_manager.get_session(session_id)
        if session_data:
            session_data.setdefault("scenario_results", {})[f"{sid}_{action}"] = result

        socketio.emit(
            "scenario_update",
            {
                "session_id": session_id,
                "scenario": sid,
                "action": action,
                "result": result,
            },
            room=session_id,
        )
        return jsonify({"id": sid, "action": action, **result})

    @app.get("/api/scenarios/<sid>/status")
    def scenario_status(sid):
        session_id = session.get("session_id")
        scenario_map = COMMANDS.get(sid, {})
        cmd = scenario_map.get("status")
        if not cmd:
            return jsonify({"error": f"Unknown scenario '{sid}'"}), 404

        result = run_cmd(cmd)

        session_data = session_manager.get_session(session_id)
        if session_data:
            session_data.setdefault("scenario_status", {})[sid] = result

        return jsonify({"id": sid, "action": "status", **result})

    # ---- Guacamole: users/configs ----
    @app.get("/api/guac/users")
    def list_guac_users():
        session_id = session.get("session_id")
        user_info = {}
        for user_type, config in GUAC_USERS.items():
            user_info[user_type] = {
                "username": config["username"],
                "display_name": config["display_name"],
                "description": config["description"],
                "color_theme": config["color_theme"],
                "connection_id": config["connection_id"],
                "has_active_token": session_manager.get_user_token(
                    session_id, user_type
                )
                is not None,
            }
        return jsonify(
            {
                "users": list(GUAC_USERS.keys()),
                "user_configs": user_info,
                "session_id": session_id,
            }
        )

    # ---- Guacamole: token (returns tokenized connection_url) ----
    @app.post("/api/guac/token/<user_type>")
    def get_token_for_user(user_type):
        session_id = session.get("session_id")
        app.logger.info(f"Getting token for {user_type} (session: {session_id})")

        existing_token = session_manager.get_user_token(session_id, user_type)
        if existing_token:
            try:
                test_response = requests.get(
                    f"{GUAC_BASE}/api/session/data/mysql/connections",
                    params={"token": existing_token},
                    timeout=5,
                    verify=False,
                )
                if test_response.status_code == 200:
                    app.logger.info(f"Using existing valid token for {user_type}")
                    connection_id = GUAC_USERS[user_type]["connection_id"]
                    return jsonify(
                        {
                            "user_type": user_type,
                            "token": existing_token,
                            "guac_base": GUAC_BASE,
                            "connection_url": tokenized_connection_url(
                                connection_id, existing_token
                            ),
                            "cached": True,
                        }
                    )
            except Exception:
                app.logger.info(
                    f"Existing token for {user_type} is invalid, getting new one"
                )

        token, status_code = get_guac_token(user_type)
        if status_code != 200:
            return jsonify({"error": token}), status_code

        session_manager.store_user_token(session_id, user_type, token)
        session_manager.add_active_connection(session_id, user_type)

        connections = get_guac_connections(token)
        connection_id = GUAC_USERS[user_type]["connection_id"]

        result = {
            "user_type": user_type,
            "token": token,
            "guac_base": GUAC_BASE,
            "connection_url": tokenized_connection_url(connection_id, token),
            "connections": connections,
            "user_config": GUAC_USERS[user_type],
            "cached": False,
        }

        socketio.emit(
            "user_connected",
            {
                "session_id": session_id,
                "user_type": user_type,
                "timestamp": datetime.now().isoformat(),
            },
            room=session_id,
        )

        return jsonify(result)

    # ---- Guacamole: auto-login HTML (redirect uses tokenized URL) ----
    @app.get("/api/guac/auto-login/<user_type>")
    def guac_auto_login(user_type):
        session_id = session.get("session_id")
        if user_type not in GUAC_USERS:
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        app.logger.info(
            f"Creating auto-login page for {user_type} (session: {session_id})"
        )

        token, status_code = get_guac_token(user_type)
        if status_code != 200:
            error_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Login Failed - {user_type.title()}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#c0392b;font-family:Arial,sans-serif}}
.error-card {{background:#fff;border-radius:10px;padding:30px;text-align:center;box-shadow:0 6px 20px rgba(0,0,0,.1);max-width:400px}}
.error-icon {{font-size:48px;color:#e74c3c;margin-bottom:15px}}
</style></head>
<body><div class="error-card">
<div class="error-icon">⚠️</div>
<h2>Login Failed</h2>
<p>{token}</p>
<button onclick="location.reload()">Retry</button>
</div></body></html>"""
            return Response(error_html, mimetype="text/html", status=status_code)

        session_manager.store_user_token(session_id, user_type, token)
        session_manager.add_active_connection(session_id, user_type)

        user_config = GUAC_USERS[user_type]
        connection_id = user_config["connection_id"]
        connection_url = tokenized_connection_url(connection_id, token)

        html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Connecting to {user_config['display_name']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{
  display:flex;justify-content:center;align-items:center;height:100vh;margin:0;
  background:linear-gradient(135deg,{user_config['color_theme']},{user_config['color_theme']}88);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}}
.connection-card {{
  background:rgba(255,255,255,0.95);border-radius:16px;padding:40px;text-align:center;
  box-shadow:0 10px 30px rgba(0,0,0,.15);border-left:6px solid {user_config['color_theme']};max-width:400px;
}}
.user-badge {{
  display:inline-block;background:{user_config['color_theme']};color:white;padding:8px 16px;border-radius:25px;
  font-size:0.85em;margin-bottom:20px;font-weight:600;
}}
.status-text {{ color:#5a6c7d;font-size:0.9em; }}
.manual-link {{ margin-top:20px;padding-top:20px;border-top:1px solid #ecf0f1;font-size:0.85em; }}
.manual-link a {{ color:{user_config['color_theme']};text-decoration:none;font-weight:500; }}
.manual-link a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
  <div class="connection-card">
    <div class="user-badge">{user_type.title()}</div>
    <h2>{user_config['display_name']}</h2>
    <p class="status-text" id="statusText">Authenticating with Guacamole server...</p>
    <div class="manual-link">
      <a href="{connection_url}" target="_blank" rel="noopener">Open connection manually</a>
    </div>
  </div>
<script>
(function() {{
  const connectionUrl = "{connection_url}";
  // Redirect using tokenized URL so Guacamole is already authenticated.
  setTimeout(() => {{
    try {{ window.location.replace(connectionUrl); }}
    catch(e) {{
      window.open(connectionUrl, "_blank");
      document.getElementById('statusText').textContent = "Connection opened in a new tab.";
    }}
  }}, 800);
}})();
</script>
</body></html>"""
        return Response(html, mimetype="text/html")

    # ---- Disconnect a single user ----
    @app.post("/api/guac/disconnect/<user_type>")
    def disconnect_user(user_type):
        session_id = session.get("session_id")
        if user_type not in GUAC_USERS:
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        session_manager.remove_active_connection(session_id, user_type)
        token = session_manager.get_user_token(session_id, user_type)
        if token:
            try:
                requests.delete(
                    f"{GUAC_BASE}/api/tokens/{token}", timeout=5, verify=False
                )
            except Exception:
                pass
        session_manager.user_tokens.get(session_id, {}).pop(user_type, None)

        socketio.emit(
            "user_disconnected",
            {
                "session_id": session_id,
                "user_type": user_type,
                "timestamp": datetime.now().isoformat(),
            },
            room=session_id,
        )
        return jsonify(
            {
                "success": True,
                "user_type": user_type,
                "message": f"{user_type} disconnected successfully",
            }
        )

    # ---- List connections for a user ----
    @app.get("/api/guac/connections/<user_type>")
    def get_user_connections(user_type):
        session_id = session.get("session_id")
        if user_type not in GUAC_USERS:
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        token = session_manager.get_user_token(session_id, user_type)
        if not token:
            return (
                jsonify(
                    {
                        "error": f"No active token for {user_type}. Please authenticate first."
                    }
                ),
                401,
            )

        connections = get_guac_connections(token)
        connection_id = GUAC_USERS[user_type]["connection_id"]
        return jsonify(
            {
                "user_type": user_type,
                "connections": connections,
                "connection_url": tokenized_connection_url(connection_id, token),
            }
        )

    # ---- Session + Bulk operations ----
    @app.get("/api/session/info")
    def session_info():
        session_id = session.get("session_id")
        session_data = session_manager.get_session(session_id)
        if not session_data:
            return jsonify({"error": "No active session"}), 404

        token_status = {
            ut: session_manager.get_user_token(session_id, ut) is not None
            for ut in GUAC_USERS.keys()
        }
        return jsonify(
            {
                **session_data,
                "token_status": token_status,
                "active_user_count": len(session_data.get("active_connections", [])),
            }
        )

    @app.post("/api/session/reset")
    def reset_session():
        session_id = session.get("session_id")
        for user_type in GUAC_USERS.keys():
            session_manager.remove_active_connection(session_id, user_type)
            token = session_manager.get_user_token(session_id, user_type)
            if token:
                try:
                    requests.delete(
                        f"{GUAC_BASE}/api/tokens/{token}", timeout=5, verify=False
                    )
                except Exception:
                    pass
        if session_id in session_manager.user_tokens:
            session_manager.user_tokens[session_id] = {}

        session["session_id"] = str(uuid.uuid4())
        new_session = session_manager.create_session(session["session_id"])

        socketio.emit(
            "session_reset",
            {
                "old_session_id": session_id,
                "new_session_id": session["session_id"],
                "timestamp": datetime.now().isoformat(),
            },
            room=session_id,
        )

        return jsonify(
            {
                "success": True,
                "message": "Session reset successfully",
                "new_session": new_session,
            }
        )

    @app.post("/api/guac/connect-all")
    def connect_all_users():
        session_id = session.get("session_id")
        results, errors = {}, {}

        for user_type in GUAC_USERS.keys():
            try:
                token, status_code = get_guac_token(user_type)
                if status_code == 200:
                    session_manager.store_user_token(session_id, user_type, token)
                    session_manager.add_active_connection(session_id, user_type)
                    connection_id = GUAC_USERS[user_type]["connection_id"]
                    results[user_type] = {
                        "success": True,
                        "token": token,
                        "connection_url": tokenized_connection_url(
                            connection_id, token
                        ),
                        "user_config": GUAC_USERS[user_type],
                    }
                else:
                    errors[user_type] = {"error": token, "status_code": status_code}
            except Exception as e:
                errors[user_type] = {"error": str(e), "status_code": 500}

        socketio.emit(
            "bulk_connect_complete",
            {
                "session_id": session_id,
                "results": results,
                "errors": errors,
                "timestamp": datetime.now().isoformat(),
            },
            room=session_id,
        )

        return jsonify(
            {
                "session_id": session_id,
                "results": results,
                "errors": errors,
                "total_connected": len(results),
                "total_errors": len(errors),
            }
        )

    @app.post("/api/guac/disconnect-all")
    def disconnect_all_users():
        session_id = session.get("session_id")
        results = {}

        for user_type in GUAC_USERS.keys():
            try:
                session_manager.remove_active_connection(session_id, user_type)
                token = session_manager.get_user_token(session_id, user_type)
                if token:
                    try:
                        requests.delete(
                            f"{GUAC_BASE}/api/tokens/{token}", timeout=5, verify=False
                        )
                    except Exception:
                        pass
                session_manager.user_tokens.get(session_id, {}).pop(user_type, None)
                results[user_type] = {
                    "success": True,
                    "message": f"{user_type} disconnected",
                }
            except Exception as e:
                results[user_type] = {"success": False, "error": str(e)}

        socketio.emit(
            "bulk_disconnect_complete",
            {
                "session_id": session_id,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            },
            room=session_id,
        )

        return jsonify(
            {
                "session_id": session_id,
                "results": results,
                "disconnected_count": sum(
                    1 for r in results.values() if r.get("success")
                ),
            }
        )

    # ---- WebSocket events ----
    @socketio.on("connect")
    def handle_connect():
        session_id = session.get("session_id")
        if session_id:
            join_room(session_id)
            app.logger.info(f"WebSocket client connected to session {session_id}")
            emit(
                "connected",
                {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Connected to lab management system",
                },
            )

    @socketio.on("disconnect")
    def handle_disconnect():
        session_id = session.get("session_id")
        if session_id:
            leave_room(session_id)
            app.logger.info(f"WebSocket client disconnected from session {session_id}")

    @socketio.on("join_session")
    def handle_join_session(data):
        session_id = data.get("session_id") or session.get("session_id")
        if session_id:
            join_room(session_id)
            emit(
                "joined_session",
                {"session_id": session_id, "timestamp": datetime.now().isoformat()},
            )

    @socketio.on("ping")
    def handle_ping():
        emit("pong", {"timestamp": datetime.now().isoformat()})

    # ---- Admin debug ----
    @app.get("/api/admin/sessions")
    def list_all_sessions():
        if not FLASK_DEBUG:
            return jsonify({"error": "Only available in debug mode"}), 403
        return jsonify(
            {
                "active_sessions": session_manager.active_sessions,
                "user_tokens": {
                    sid: {
                        ut: "***" + token[-4:] if token else None
                        for ut, token in tokens.items()
                    }
                    for sid, tokens in session_manager.user_tokens.items()
                },
                "total_sessions": len(session_manager.active_sessions),
            }
        )

    @app.post("/api/admin/cleanup")
    def cleanup_expired_sessions():
        if not FLASK_DEBUG:
            return jsonify({"error": "Only available in debug mode"}), 403
        before = len(session_manager.active_sessions)
        session_manager.cleanup_expired_sessions()
        after = len(session_manager.active_sessions)
        return jsonify({"cleaned_up": before - after, "remaining_sessions": after})

    # ---- Background cleanup ----
    def background_cleanup():
        while True:
            try:
                time.sleep(300)
                session_manager.cleanup_expired_sessions()
            except Exception as e:
                app.logger.error(f"Error in background cleanup: {e}")

    cleanup_thread = threading.Thread(target=background_cleanup, daemon=True)
    cleanup_thread.start()

    app.socketio = socketio
    return app


def main():
    app = create_app()
    if FLASK_DEBUG:
        print(
            f"""
🔧 Cybersecurity Lab Management Server
=====================================
🌐 Server: http://{FLASK_HOST}:{FLASK_PORT}
🎯 Guacamole: {GUAC_BASE}
📁 Scripts: {SCRIPTS_ROOT}
👥 Users: {', '.join(GUAC_USERS.keys())}
🔒 Session Timeout: {SESSION_TIMEOUT}s
=====================================
        """
        )
    try:
        app.socketio.run(
            app,
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            use_reloader=FLASK_USE_RELOADER,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
