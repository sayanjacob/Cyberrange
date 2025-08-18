#!/usr/bin/env python3
import os
import sys
import logging
import shlex
import subprocess
import json
from urllib.parse import urlencode
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import threading
import time
from functools import wraps

import requests
from flask import Flask, app, jsonify, request, Response, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix

# =========================
# Configuration (env vars)
# =========================
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:4200, http://127.0.0.1:4200,*"
).split(",")

SCRIPTS_ROOT = os.path.abspath(
    os.getenv("SCRIPTS_ROOT", os.path.join(os.path.dirname(__file__), "scripts"))
)

# Guacamole base (must point to /guacamole)
GUAC_BASE = os.getenv("GUAC_BASE", "http://20.197.40.109:8080/guacamole")

# Two mapped users (you can switch to env-only by removing defaults)
GUAC_USERS = {
    "victim": {
        "username": "victim",
        "password": "victim",
        "connection_id": "2",
        "display_name": "Victim Machine",
        "description": "Target system for security testing",
        "color_theme": "#3498db",
    },
    "attacker": {
        "username": "attacker",
        "password": "attacker",
        "connection_id": "4",
        "display_name": "Attacker Machine",
        "description": "Penetration testing platform",
        "color_theme": "#e74c3c",
    },
}

GUAC_TOKEN_TIMEOUT = 3600
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
FLASK_USE_RELOADER = os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"

SESSION_TIMEOUT = 3600  # 1 hour
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")


# =========================
# Enhanced Logging Setup
# =========================
def setup_logging():
    """Setup comprehensive logging with different levels for different components"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Main application logger
    app_logger = logging.getLogger("cybersec_lab")
    app_logger.setLevel(logging.DEBUG if FLASK_DEBUG else logging.INFO)

    # Security events logger
    security_logger = logging.getLogger("security_events")
    security_logger.setLevel(logging.INFO)

    # Performance logger
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.INFO)

    # Formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if FLASK_DEBUG else logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # File handlers
    if not FLASK_DEBUG:  # Only create file logs in production
        app_file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        app_file_handler.setLevel(logging.INFO)
        app_file_handler.setFormatter(detailed_formatter)

        security_file_handler = logging.FileHandler(
            os.path.join(log_dir, "security.log")
        )
        security_file_handler.setLevel(logging.INFO)
        security_file_handler.setFormatter(detailed_formatter)

        perf_file_handler = logging.FileHandler(
            os.path.join(log_dir, "performance.log")
        )
        perf_file_handler.setLevel(logging.INFO)
        perf_file_handler.setFormatter(detailed_formatter)

        app_logger.addHandler(app_file_handler)
        security_logger.addHandler(security_file_handler)
        perf_logger.addHandler(perf_file_handler)

    # Add console handlers
    for logger in [app_logger, security_logger, perf_logger]:
        logger.addHandler(console_handler)

    return app_logger, security_logger, perf_logger


# Initialize loggers
app_logger, security_logger, perf_logger = setup_logging()


# =========================
# Performance Monitoring Decorator
# =========================
def monitor_performance(operation_name: str):
    """Decorator to monitor API endpoint performance"""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # Convert to ms
                perf_logger.info(
                    f"PERF: {operation_name} completed in {duration:.2f}ms"
                )
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                perf_logger.error(
                    f"PERF: {operation_name} failed after {duration:.2f}ms - {str(e)}"
                )
                raise

        return wrapper

    return decorator


# =========================
# Enhanced Session Management
# =========================
class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.user_tokens: Dict[str, Dict[str, str]] = {}
        self.connection_status: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background thread for session cleanup"""

        def cleanup_loop():
            while True:
                try:
                    self.cleanup_expired_sessions()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    app_logger.error(f"Session cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
        app_logger.info("Session cleanup thread started")

    def create_session(self, session_id: str) -> Dict[str, Any]:
        with self.lock:
            session_data = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "active_connections": [],
                "scenario_status": {},
                "user_preferences": {},
                "client_info": {},
            }
            self.active_sessions[session_id] = session_data
            self.user_tokens[session_id] = {}
            app_logger.info(f"Created new session: {session_id[:8]}...")
            security_logger.info(f"SESSION_CREATED: {session_id}")
            return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            session = self.active_sessions.get(session_id)
            if session:
                app_logger.debug(f"Retrieved session: {session_id[:8]}...")
            else:
                app_logger.warning(f"Session not found: {session_id[:8]}...")
            return session

    def update_session_activity(self, session_id: str):
        with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id][
                    "last_activity"
                ] = datetime.now().isoformat()
                app_logger.debug(f"Updated activity for session: {session_id[:8]}...")

    def store_user_token(self, session_id: str, user_type: str, token: str):
        with self.lock:
            if session_id not in self.user_tokens:
                self.user_tokens[session_id] = {}
            self.user_tokens[session_id][user_type] = token
            app_logger.info(
                f"Stored token for {user_type} in session {session_id[:8]}..."
            )
            security_logger.info(
                f"TOKEN_STORED: session={session_id}, user_type={user_type}"
            )

    def get_user_token(self, session_id: str, user_type: str) -> Optional[str]:
        with self.lock:
            token = self.user_tokens.get(session_id, {}).get(user_type)
            if token:
                app_logger.debug(
                    f"Retrieved token for {user_type} in session {session_id[:8]}..."
                )
            else:
                app_logger.debug(
                    f"No token found for {user_type} in session {session_id[:8]}..."
                )
            return token

    def remove_user_token(self, session_id: str, user_type: str):
        with self.lock:
            if session_id in self.user_tokens:
                removed = self.user_tokens[session_id].pop(user_type, None)
                if removed:
                    app_logger.info(
                        f"Removed token for {user_type} in session {session_id[:8]}..."
                    )
                    security_logger.info(
                        f"TOKEN_REMOVED: session={session_id}, user_type={user_type}"
                    )

    def add_active_connection(self, session_id: str, user_type: str):
        with self.lock:
            if session_id in self.active_sessions:
                connections = self.active_sessions[session_id]["active_connections"]
                if user_type not in connections:
                    connections.append(user_type)
                    app_logger.info(
                        f"Added active connection {user_type} to session {session_id[:8]}..."
                    )
                    security_logger.info(
                        f"CONNECTION_ADDED: session={session_id}, user_type={user_type}"
                    )

    def remove_active_connection(self, session_id: str, user_type: str):
        with self.lock:
            if session_id in self.active_sessions:
                connections = self.active_sessions[session_id]["active_connections"]
                if user_type in connections:
                    connections.remove(user_type)
                    app_logger.info(
                        f"Removed active connection {user_type} from session {session_id[:8]}..."
                    )
                    security_logger.info(
                        f"CONNECTION_REMOVED: session={session_id}, user_type={user_type}"
                    )

    def cleanup_expired_sessions(self):
        with self.lock:
            current_time = datetime.now()
            expired_sessions = []
            for session_id, session_data in self.active_sessions.items():
                try:
                    last_activity = datetime.fromisoformat(
                        session_data["last_activity"]
                    )
                    if (current_time - last_activity).seconds > SESSION_TIMEOUT:
                        expired_sessions.append(session_id)
                except Exception as e:
                    app_logger.error(
                        f"Error checking session expiry for {session_id}: {e}"
                    )
                    expired_sessions.append(session_id)  # Remove corrupted sessions

            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                if session_id in self.user_tokens:
                    del self.user_tokens[session_id]
                app_logger.info(f"Cleaned up expired session: {session_id[:8]}...")
                security_logger.info(f"SESSION_EXPIRED: {session_id}")

            if expired_sessions:
                app_logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


session_manager = SessionManager()


# =========================
# Enhanced Guacamole Functions
# =========================
@monitor_performance("get_guac_token")
def get_guac_token(user_type: str, force_new: bool = False) -> Tuple[str, str, int]:
    """Get Guacamole authentication token with enhanced error handling and logging"""
    if user_type not in GUAC_USERS:
        error_msg = f"Invalid user type: {user_type}"
        app_logger.error(error_msg)
        return error_msg, "", 400

    user_config = GUAC_USERS[user_type]
    app_logger.info(
        f"Requesting Guacamole token for {user_type} (force_new={force_new})"
    )

    try:
        # Prepare authentication data
        auth_data = {
            "username": user_config["username"],
            "password": user_config["password"],
        }

        app_logger.debug(f"Authenticating with Guacamole API at {GUAC_BASE}/api/tokens")

        # Make authentication request
        response = requests.post(
            f"{GUAC_BASE}/api/tokens",
            data=auth_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=GUAC_TOKEN_TIMEOUT,
            verify=False,
        )

        app_logger.debug(f"Guacamole auth response status: {response.status_code}")

        if response.status_code != 200:
            error_msg = f"Guacamole authentication failed for {user_type}: HTTP {response.status_code}"
            app_logger.error(error_msg)
            security_logger.warning(
                f"AUTH_FAILED: user_type={user_type}, status={response.status_code}"
            )
            return error_msg, "", response.status_code

        data = response.json()
        token = data.get("authToken")
        ds = data.get("dataSource", "mysql")  # Default to mysql

        if not token:
            error_msg = f"No authToken received for {user_type}"
            app_logger.error(error_msg)
            security_logger.warning(f"TOKEN_MISSING: user_type={user_type}")
            return error_msg, "", 500

        app_logger.info(f"Successfully obtained token for {user_type}")
        security_logger.info(f"TOKEN_OBTAINED: user_type={user_type}, datasource={ds}")
        return token, ds, 200

    except requests.exceptions.Timeout:
        error_msg = f"Timeout connecting to Guacamole for {user_type}"
        app_logger.error(error_msg)
        return error_msg, "", 408
    except requests.exceptions.ConnectionError:
        error_msg = f"Connection error to Guacamole for {user_type}"
        app_logger.error(error_msg)
        return error_msg, "", 503
    except Exception as e:
        error_msg = f"Unexpected error getting token for {user_type}: {str(e)}"
        app_logger.error(error_msg)
        return error_msg, "", 500


def validate_guac_token(token: str) -> bool:
    """Validate if a Guacamole token is still valid with enhanced logging"""
    try:
        app_logger.debug("Validating Guacamole token")
        headers = {"Accept": "application/json"}
        response = requests.get(
            f"{GUAC_BASE}/api/session/data/mysql/connections",
            headers=headers,
            params={"token": token},
            timeout=10,
            verify=False,
        )
        is_valid = response.status_code == 200
        app_logger.debug(f"Token validation result: {is_valid}")
        return is_valid
    except Exception as e:
        app_logger.error(f"Token validation error: {e}")
        return False


def get_guac_connections(token: str, data_source: str) -> dict:
    """Get Guacamole connections with enhanced logging"""
    try:
        app_logger.debug(f"Fetching connections for datasource: {data_source}")
        r = requests.get(
            f"{GUAC_BASE}/api/session/data/{data_source}/connections",
            headers={"Accept": "application/json"},
            params={"token": token},
            timeout=GUAC_TOKEN_TIMEOUT,
            verify=False,
        )

        if r.status_code == 200:
            connections = r.json()
            app_logger.info(f"Retrieved {len(connections)} connections from Guacamole")
            return connections
        else:
            error_msg = f"HTTP {r.status_code}: {r.text}"
            app_logger.error(f"Failed to get connections: {error_msg}")
            return {"error": error_msg}

    except Exception as e:
        error_msg = f"Exception getting connections: {str(e)}"
        app_logger.error(error_msg)
        return {"error": error_msg}


def resolve_connection_id(user_type: str, token: str, data_source: str) -> str:
    """Resolve connection ID with enhanced error handling"""
    app_logger.debug(f"Resolving connection ID for {user_type}")

    # Use configured ID if present
    cfg = str(GUAC_USERS[user_type].get("connection_id", "")).strip()
    if cfg:
        app_logger.info(f"Using configured connection ID {cfg} for {user_type}")
        return cfg

    # Get available connections
    conns = get_guac_connections(token, data_source)
    if "error" in conns:
        raise RuntimeError(conns["error"])

    ids = list(conns.keys())
    app_logger.debug(f"Available connection IDs: {ids}")

    if len(ids) == 1:
        app_logger.info(
            f"Using single available connection ID {ids[0]} for {user_type}"
        )
        return ids[0]

    # Try to match by name if there are multiple
    uname = GUAC_USERS[user_type]["username"].lower()
    for cid, meta in conns.items():
        name = str(meta.get("name", "")).lower()
        if name in (uname, user_type.lower()):
            app_logger.info(f"Matched connection ID {cid} by name for {user_type}")
            return cid

    names = [v.get("name") for v in conns.values()]
    error_msg = (
        f"Multiple connections visible for {user_type}. "
        f"Set connection_id explicitly. Found: {names}"
    )
    app_logger.error(error_msg)
    raise RuntimeError(error_msg)


def invalidate_guac_token(token: str):
    """Explicitly invalidate a Guacamole token with logging"""
    try:
        app_logger.debug("Invalidating Guacamole token")
        response = requests.delete(
            f"{GUAC_BASE}/api/tokens/{token}", timeout=5, verify=False
        )
        if response.status_code == 204:
            app_logger.info("Token successfully invalidated")
        else:
            app_logger.warning(
                f"Token invalidation returned status: {response.status_code}"
            )
    except Exception as e:
        app_logger.error(f"Error invalidating token: {e}")


def tokenized_connection_url(
    connection_id: str, token: str, data_source: str = "mysql"
) -> str:
    """Generate tokenized connection URL"""
    cid = str(connection_id).strip()
    ds = str(data_source).strip()
    qs = urlencode({"token": str(token), "embed": "true", "resize": "scale"})
    url = f"{GUAC_BASE.rstrip('/')}/#/client/{ds}/{cid}?{qs}"
    app_logger.debug(f"Generated connection URL for connection {cid}")
    return url


# =========================
# Enhanced Flask App Factory
# =========================
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = False  # Set to True in production with HTTPS
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=SESSION_TIMEOUT)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Enhanced CORS configuration
    CORS(
        app,
        resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # Socket.IO with enhanced configuration
    socketio = SocketIO(
        app,
        cors_allowed_origins=ALLOWED_ORIGINS,
        logger=FLASK_DEBUG,
        engineio_logger=FLASK_DEBUG,
        async_mode="threading",  # Explicit async mode
    )

    # Enhanced request logging
    @app.before_request
    def before_request():
        # Initialize session if needed
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
            session.permanent = True
            session_data = session_manager.create_session(session["session_id"])
        else:
            session_manager.update_session_activity(session["session_id"])

        # Log request details
        if FLASK_DEBUG:
            try:
                body = request.get_data(as_text=True) or ""
                body_preview = body[:200] + ("..." if len(body) > 200 else "")
            except Exception:
                body_preview = "<unavailable>"

            app_logger.debug(
                f"REQUEST: {request.remote_addr} {request.method} {request.path} "
                f"Session: {session.get('session_id', 'none')[:8]}... "
                f"User-Agent: {request.headers.get('User-Agent', 'unknown')[:50]}... "
                f"Body: {body_preview}"
            )

    @app.after_request
    def after_request(response):
        if FLASK_DEBUG:
            app_logger.debug(
                f"RESPONSE: {response.status} for {request.method} {request.path}"
            )
        return response

    # =========================
    # API Endpoints
    # =========================

    @app.get("/api/health")
    @monitor_performance("health_check")
    def health():
        """Enhanced health check with system status"""
        try:
            # Basic connectivity test to Guacamole
            guac_status = "unknown"
            try:
                response = requests.get(
                    f"{GUAC_BASE}/api/languages", timeout=5, verify=False
                )
                guac_status = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception:
                guac_status = "unreachable"

            health_data = {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "session_id": session.get("session_id"),
                "guac_base": GUAC_BASE,
                "guac_status": guac_status,
                "active_sessions": len(session_manager.active_sessions),
                "total_active_connections": sum(
                    len(s.get("active_connections", []))
                    for s in session_manager.active_sessions.values()
                ),
                "version": "2.0.0",  # Add version tracking
            }

            app_logger.debug("Health check completed successfully")
            return jsonify(health_data)

        except Exception as e:
            app_logger.error(f"Health check failed: {e}")
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    @app.get("/api/status")
    @monitor_performance("status_check")
    def status():
        """Enhanced status endpoint with detailed session info"""
        try:
            session_id = session.get("session_id")
            session_data = session_manager.get_session(session_id)

            # Validate all stored tokens
            validated_users = {}
            for user_type, config in GUAC_USERS.items():
                token = session_manager.get_user_token(session_id, user_type)
                token_valid = validate_guac_token(token) if token else False

                validated_users[user_type] = {
                    "username": config["username"],
                    "display_name": config["display_name"],
                    "description": config["description"],
                    "color_theme": config["color_theme"],
                    "connection_id": config["connection_id"],
                    "has_active_token": token is not None,
                    "token_valid": token_valid,
                    "last_activity": (
                        session_data.get("last_activity") if session_data else None
                    ),
                }

            status_data = {
                "session": session_data,
                "guac_users": validated_users,
                "system_info": {
                    "flask_debug": FLASK_DEBUG,
                    "session_timeout": SESSION_TIMEOUT,
                    "scripts_root": SCRIPTS_ROOT,
                },
            }

            app_logger.debug(f"Status check for session {session_id[:8]}...")
            return jsonify(status_data)

        except Exception as e:
            app_logger.error(f"Status check failed: {e}")
            return jsonify({"error": str(e)}), 500

    @app.post("/api/guac/token/<user_type>")
    @monitor_performance("get_token")
    def get_token_for_user(user_type):
        """Enhanced token endpoint with comprehensive validation"""
        session_id = session.get("session_id")

        if user_type not in GUAC_USERS:
            app_logger.warning(f"Invalid user type requested: {user_type}")
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        try:
            app_logger.info(
                f"Token requested for {user_type} in session {session_id[:8]}..."
            )

            # Get fresh token
            token, ds, status = get_guac_token(user_type, force_new=True)
            if status != 200:
                return jsonify({"error": token}), status

            # Resolve connection ID
            conn_id = resolve_connection_id(user_type, token, ds)

            # Generate connection URL
            url = tokenized_connection_url(conn_id, token, ds)

            # Store token in session
            session_manager.store_user_token(session_id, user_type, token)

            response_data = {
                "ok": True,
                "connection_url": url,
                "user_type": user_type,
                "connection_id": conn_id,
                "data_source": ds,
            }

            app_logger.info(f"Token successfully generated for {user_type}")
            return jsonify(response_data)

        except Exception as e:
            app_logger.error(f"Token generation failed for {user_type}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.get("/api/guac/auto-login/<user_type>")
    @monitor_performance("auto_login")
    def guac_auto_login(user_type):
        """Enhanced auto-login with better error handling and logging"""
        session_id = session.get("session_id")

        if user_type not in GUAC_USERS:
            app_logger.warning(f"Invalid user type for auto-login: {user_type}")
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        app_logger.info(
            f"Auto-login requested for {user_type} in session {session_id[:8]}..."
        )

        try:
            # Get fresh token for auto-login
            token, ds, status_code = get_guac_token(user_type, force_new=True)
            if status_code != 200:
                error_html = self._generate_error_page(user_type, token)
                return Response(error_html, mimetype="text/html", status=status_code)

            # Store token and mark connection as active
            session_manager.store_user_token(session_id, user_type, token)
            session_manager.add_active_connection(session_id, user_type)

            # Generate connection details
            user_config = GUAC_USERS[user_type]
            connection_id = resolve_connection_id(user_type, token, ds)
            connection_url = tokenized_connection_url(connection_id, token, ds)

            # Generate enhanced HTML page
            html = self._generate_connection_page(
                user_type, user_config, connection_url
            )

            app_logger.info(f"Auto-login page generated for {user_type}")
            return Response(html, mimetype="text/html")

        except Exception as e:
            app_logger.error(f"Auto-login failed for {user_type}: {e}")
            error_html = self._generate_error_page(user_type, str(e))
            return Response(error_html, mimetype="text/html", status=500)

    def _generate_error_page(self, user_type: str, error_message: str) -> str:
        """Generate enhanced error page"""
        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Connection Failed - {user_type.title()}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #c0392b, #e74c3c);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .error-card {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,.2);
            max-width: 500px;
            border-left: 6px solid #e74c3c;
        }}
        .error-icon {{ font-size: 48px; color: #e74c3c; margin-bottom: 20px; }}
        .retry-btn {{
            background: #e74c3c;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 20px;
            transition: background 0.3s;
        }}
        .retry-btn:hover {{ background: #c0392b; }}
        .error-details {{ margin-top: 15px; font-size: 14px; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="error-card">
        <div class="error-icon">⚠️</div>
        <h2>Connection Failed</h2>
        <p><strong>Unable to connect to {user_type.title()} machine</strong></p>
        <button class="retry-btn" onclick="location.reload()">Retry Connection</button>
        <div class="error-details">
            <details>
                <summary>Technical Details</summary>
                <p>{error_message}</p>
            </details>
        </div>
    </div>
    <script>
        // Auto-retry after 5 seconds
        setTimeout(() => {{
            if (confirm('Connection failed. Would you like to retry automatically?')) {{
                location.reload();
            }}
        }}, 5000);
    </script>
</body>
</html>"""

    def _generate_connection_page(
        self, user_type: str, user_config: dict, connection_url: str
    ) -> str:
        """Generate enhanced connection page with better UX"""
        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Connecting to {user_config['display_name']}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, {user_config['color_theme']}, {user_config['color_theme']}88);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .connection-card {{
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,.15);
            border-left: 6px solid {user_config['color_theme']};
            max-width: 450px;
            min-width: 350px;
        }}
        .user-badge {{
            display: inline-block;
            background: {user_config['color_theme']};
            color: white;
            padding: 8px 16px;
            border-radius: 25px;
            font-size: 0.85em;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        .status-text {{ 
            color: #5a6c7d; 
            font-size: 0.9em; 
            margin: 20px 0;
        }}
        .loading-spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid {user_config['color_theme']};
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .manual-link {{ 
            margin-top: 25px; 
            padding-top: 20px; 
            border-top: 1px solid #ecf0f1; 
            font-size: 0.85em; 
        }}
        .manual-link a {{ 
            color: {user_config['color_theme']}; 
            text-decoration: none; 
            font-weight: 500; 
            padding: 8px 16px;
            border: 1px solid {user_config['color_theme']};
            border-radius: 6px;
            display: inline-block;
            transition: all 0.3s;
        }}
        .manual-link a:hover {{ 
            background: {user_config['color_theme']};
            color: white;
        }}
        .connection-info {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.8em;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="connection-card">
        <div class="user-badge">{user_type.title()}</div>
        <h2>{user_config['display_name']}</h2>
        <div class="loading-spinner"></div>
        <p class="status-text" id="statusText">Establishing secure connection...</p>
        
        <div class="connection-info">
            <strong>Description:</strong> {user_config['description']}<br>
            <strong>Status:</strong> <span id="connectionStatus">Connecting...</span>
        </div>
        
        <div class="manual-link">
            <a href="{connection_url}" target="_blank" rel="noopener" id="manualLink">
                Open Connection Manually
            </a>
        </div>
    </div>

    <script>
        (function() {{
            const connectionUrl = "{connection_url}";
            let attemptCount = 0;
            const maxAttempts = 3;
            
            function updateStatus(message, isError = false) {{
                const statusEl = document.getElementById('statusText');
                const connectionStatusEl = document.getElementById('connectionStatus');
                statusEl.textContent = message;
                connectionStatusEl.textContent = isError ? 'Failed' : 'In Progress';
                statusEl.style.color = isError ? '#e74c3c' : '#5a6c7d';
            }}
            
            function attemptConnection() {{
                attemptCount++;
                updateStatus(`Attempting connection (${attemptCount}/${maxAttempts})...`);
                
                try {{ 
                    // Try to redirect to the connection
                    window.location.replace(connectionUrl); 
                }}
                catch(e) {{
                    console.error('Redirect failed:', e);
                    // Fallback: open in new window
                    const newWindow = window.open(connectionUrl, "_blank", "noopener,noreferrer");
                    if (newWindow) {{
                        updateStatus("Connection opened in new tab.");
                        document.getElementById('connectionStatus').textContent = 'Opened';
                    }} else {{
                        updateStatus("Pop-up blocked. Please use manual link.", true);
                    }}
                }}
            }}
            
            // Initial connection attempt after delay
            setTimeout(attemptConnection, 2000);
            
            // Add click handler for manual link
            document.getElementById('manualLink').addEventListener('click', function(e) {{
                e.preventDefault();
                window.open(connectionUrl, '_blank', 'noopener,noreferrer');
                updateStatus("Connection opened manually.");
                document.getElementById('connectionStatus').textContent = 'Opened';
            }});
            
            // Auto-retry logic with exponential backoff
            let retryTimeout = 5000;
            function scheduleRetry() {{
                if (attemptCount < maxAttempts) {{
                    setTimeout(() => {{
                        retryTimeout *= 1.5; // Exponential backoff
                        attemptConnection();
                        scheduleRetry();
                    }}, retryTimeout);
                }} else {{
                    updateStatus("Auto-connection attempts exhausted. Please use manual link.", true);
                }}
            }}
            
            // Only schedule retries if the page is still visible
            if (!document.hidden) {{
                setTimeout(scheduleRetry, 3000);
            }}
        }})();
    </script>
</body>
</html>"""

    @app.post("/api/guac/disconnect/<user_type>")
    @monitor_performance("disconnect_user")
    def disconnect_user(user_type):
        """Enhanced disconnect endpoint with comprehensive cleanup"""
        session_id = session.get("session_id")

        if user_type not in GUAC_USERS:
            app_logger.warning(f"Invalid user type for disconnect: {user_type}")
            return jsonify({"error": f"Invalid user type: {user_type}"}), 400

        try:
            app_logger.info(
                f"Disconnect requested for {user_type} in session {session_id[:8]}..."
            )

            # Remove active connection first
            session_manager.remove_active_connection(session_id, user_type)

            # Get and invalidate token
            token = session_manager.get_user_token(session_id, user_type)
            if token:
                invalidate_guac_token(token)
                session_manager.remove_user_token(session_id, user_type)
                app_logger.info(f"Token invalidated for {user_type}")
            else:
                app_logger.info(f"No active token found for {user_type}")

            # Emit socket event for real-time updates
            socketio.emit(
                "user_disconnected",
                {
                    "session_id": session_id,
                    "user_type": user_type,
                    "timestamp": datetime.now().isoformat(),
                },
                room=session_id,
            )

            response_data = {
                "success": True,
                "user_type": user_type,
                "message": f"{user_type} disconnected successfully",
                "timestamp": datetime.now().isoformat(),
            }

            app_logger.info(f"Successfully disconnected {user_type}")
            security_logger.info(
                f"USER_DISCONNECTED: session={session_id}, user_type={user_type}"
            )

            return jsonify(response_data)

        except Exception as e:
            app_logger.error(f"Disconnect failed for {user_type}: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/guac/disconnect-all", methods=["POST", "DELETE", "OPTIONS"])
    @monitor_performance("disconnect_all")
    def disconnect_all():
        """Enhanced disconnect-all with detailed results and cleanup"""
        session_id = session.get("session_id")
        results = {}
        success_count = 0
        error_count = 0

        app_logger.info(f"Disconnect-all requested for session {session_id[:8]}...")

        try:
            for user_type in GUAC_USERS.keys():
                try:
                    token = session_manager.get_user_token(session_id, user_type)
                    if token:
                        # Validate token before attempting to invalidate
                        if validate_guac_token(token):
                            invalidate_guac_token(token)
                            results[user_type] = "disconnected"
                            success_count += 1
                        else:
                            results[user_type] = "token_already_invalid"
                            success_count += 1
                    else:
                        results[user_type] = "no_active_token"
                        success_count += 1

                    # Clean up session data regardless
                    session_manager.remove_user_token(session_id, user_type)
                    session_manager.remove_active_connection(session_id, user_type)

                except Exception as e:
                    results[user_type] = f"error: {str(e)}"
                    error_count += 1
                    app_logger.error(f"Error disconnecting {user_type}: {e}")

            # Emit socket event for all disconnections
            socketio.emit(
                "all_users_disconnected",
                {
                    "session_id": session_id,
                    "results": results,
                    "timestamp": datetime.now().isoformat(),
                },
                room=session_id,
            )

            response_data = {
                "ok": True,
                "results": results,
                "summary": {
                    "total_processed": len(GUAC_USERS),
                    "successful": success_count,
                    "errors": error_count,
                },
                "timestamp": datetime.now().isoformat(),
            }

            app_logger.info(
                f"Disconnect-all completed: {success_count} successful, {error_count} errors"
            )
            security_logger.info(
                f"ALL_USERS_DISCONNECTED: session={session_id}, success={success_count}, errors={error_count}"
            )

            return jsonify(response_data)

        except Exception as e:
            app_logger.error(f"Disconnect-all failed: {e}")
            return jsonify({"error": str(e)}), 500

    # =========================
    # WebSocket Event Handlers
    # =========================

    @socketio.on("connect")
    def handle_connect():
        """Enhanced WebSocket connection handler"""
        session_id = session.get("session_id")
        if session_id:
            join_room(session_id)
            app_logger.info(f"WebSocket client connected to room {session_id[:8]}...")

            # Send current session status
            session_data = session_manager.get_session(session_id)
            emit(
                "session_status",
                {
                    "session_id": session_id,
                    "active_connections": (
                        session_data.get("active_connections", [])
                        if session_data
                        else []
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            )
        else:
            app_logger.warning("WebSocket connection without valid session")
            emit("error", {"message": "No valid session"})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Enhanced WebSocket disconnection handler"""
        session_id = session.get("session_id")
        if session_id:
            leave_room(session_id)
            app_logger.info(
                f"WebSocket client disconnected from room {session_id[:8]}..."
            )

    @socketio.on("ping")
    def handle_ping():
        """WebSocket ping/pong for connection health"""
        emit("pong", {"timestamp": datetime.now().isoformat()})

    # =========================
    # Error Handlers
    # =========================

    @app.errorhandler(404)
    def not_found(error):
        app_logger.warning(f"404 error for {request.path}")
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app_logger.error(f"500 error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app_logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

    # Store socketio reference
    app.socketio = socketio

    # Log successful app creation
    app_logger.info("Flask application created successfully")

    return app


# =========================
# Application Entry Point
# =========================
def main():
    """Enhanced main function with better startup logging"""
    try:
        # Validate environment
        if SECRET_KEY == "your-secret-key-change-in-production":
            app_logger.warning(
                "⚠️  Using default SECRET_KEY - change this in production!"
            )
            security_logger.warning("DEFAULT_SECRET_KEY_IN_USE")

        # Create Flask app
        app = create_app()

        # Startup information
        if FLASK_DEBUG:
            startup_info = f"""
🔧 Cybersecurity Lab Management Server v2.0.0
================================================
🌐 Server: http://{FLASK_HOST}:{FLASK_PORT}
🎯 Guacamole: {GUAC_BASE}
📁 Scripts: {SCRIPTS_ROOT}
👥 Users: {', '.join(GUAC_USERS.keys())}
⏱️  Session Timeout: {SESSION_TIMEOUT}s
🔒 CORS Origins: {ALLOWED_ORIGINS}
🐛 Debug Mode: {FLASK_DEBUG}
📊 Performance Monitoring: Enabled
🔐 Security Logging: Enabled
================================================
"""
            print(startup_info)
            app_logger.info("Server starting in DEBUG mode")
        else:
            app_logger.info("Server starting in PRODUCTION mode")

        # Test Guacamole connectivity
        try:
            response = requests.get(
                f"{GUAC_BASE}/api/languages", timeout=10, verify=False
            )
            if response.status_code == 200:
                app_logger.info("✅ Guacamole connectivity test passed")
            else:
                app_logger.warning(
                    f"⚠️  Guacamole connectivity test returned {response.status_code}"
                )
        except Exception as e:
            app_logger.error(f"❌ Guacamole connectivity test failed: {e}")

        # Start the server
        security_logger.info("SERVER_STARTING")
        app.socketio.run(
            app,
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            use_reloader=FLASK_USE_RELOADER,
            allow_unsafe_werkzeug=True,
        )

    except KeyboardInterrupt:
        app_logger.info("🛑 Server shutdown requested by user")
        security_logger.info("SERVER_STOPPED_BY_USER")
    except Exception as e:
        app_logger.error(f"❌ Server startup error: {e}")
        security_logger.error(f"SERVER_STARTUP_ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
