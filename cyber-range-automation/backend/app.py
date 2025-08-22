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
# PRODUCTION CHANGES: Updated defaults for nginx deployment
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://20.197.40.109,http://localhost:4200,http://127.0.0.1:4200,*"
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

# PRODUCTION CHANGES: Updated for nginx deployment
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")  # Only bind to localhost
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"  # Default to false
FLASK_USE_RELOADER = os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"

SESSION_TIMEOUT = 3600  # 1 hour
# PRODUCTION CHANGES: Generate secure secret key
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())

# PRODUCTION CHANGES: Add SSL/TLS configuration
SSL_CONTEXT = None
if os.getenv("SSL_CERT") and os.getenv("SSL_KEY"):
    SSL_CONTEXT = (os.getenv("SSL_CERT"), os.getenv("SSL_KEY"))


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

    # Console handler - PRODUCTION CHANGE: Less verbose in production
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Always INFO or above for console
    console_handler.setFormatter(simple_formatter)

    # PRODUCTION CHANGES: Always create file logs for production monitoring
    app_file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(detailed_formatter)

    security_file_handler = logging.FileHandler(os.path.join(log_dir, "security.log"))
    security_file_handler.setLevel(logging.INFO)
    security_file_handler.setFormatter(detailed_formatter)

    perf_file_handler = logging.FileHandler(os.path.join(log_dir, "performance.log"))
    perf_file_handler.setLevel(logging.INFO)
    perf_file_handler.setFormatter(detailed_formatter)

    # Add handlers to loggers
    for logger in [app_logger, security_logger, perf_logger]:
        logger.addHandler(console_handler)
        logger.addHandler(
            app_file_handler
            if logger == app_logger
            else (
                security_file_handler
                if logger == security_logger
                else perf_file_handler
            )
        )

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


# [Keep all the existing Guacamole functions - they remain the same]
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

    # PRODUCTION CHANGES: Enhanced security settings
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = False  # True in production
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=SESSION_TIMEOUT)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # PRODUCTION CHANGES: Improved proxy handling for nginx
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1  # nginx -> gunicorn
    )

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
        async_mode="threading",
        # PRODUCTION CHANGES: Additional socketio config for nginx
        ping_timeout=60,
        ping_interval=25,
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

        # PRODUCTION CHANGES: Log real client IP through nginx
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if FLASK_DEBUG:
            try:
                body = request.get_data(as_text=True) or ""
                body_preview = body[:200] + ("..." if len(body) > 200 else "")
            except Exception:
                body_preview = "<unavailable>"

            app_logger.debug(
                f"REQUEST: {client_ip} {request.method} {request.path} "
                f"Session: {session.get('session_id', 'none')[:8]}... "
                f"User-Agent: {request.headers.get('User-Agent', 'unknown')[:50]}... "
                f"Body: {body_preview}"
            )

    @app.after_request
    def after_request(response):
        # PRODUCTION CHANGES: Add security headers
        if not FLASK_DEBUG:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"

        if FLASK_DEBUG:
            app_logger.debug(
                f"RESPONSE: {response.status} for {request.method} {request.path}"
            )
        return response

    # [Keep all existing API endpoints - they remain the same]
    # ... [All the API endpoints from original code] ...

    # Store socketio reference
    app.socketio = socketio

    # Log successful app creation
    app_logger.info("Flask application created successfully")

    return app


# =========================
# PRODUCTION CHANGES: WSGI Entry Point
# =========================
def create_wsgi_app():
    """Create WSGI application for production deployment"""
    return create_app()


# =========================
# Application Entry Point
# =========================
def main():
    """Enhanced main function with production considerations"""
    try:
        # PRODUCTION CHANGES: Environment validation
        if not FLASK_DEBUG and SECRET_KEY == "your-secret-key-change-in-production":
            app_logger.error("❌ SECRET_KEY must be set in production!")
            sys.exit(1)

        # Validate required environment variables
        required_env_vars = []
        if not FLASK_DEBUG:
            required_env_vars.extend(["SECRET_KEY"])

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            app_logger.error(
                f"❌ Missing required environment variables: {missing_vars}"
            )
            sys.exit(1)

        # Create Flask app
        app = create_app()

        # PRODUCTION CHANGES: Different startup info for production
        if FLASK_DEBUG:
            startup_info = f"""
🔧 Cybersecurity Lab Management Server v2.0.0 [DEVELOPMENT]
============================================================
🌐 Server: http://{FLASK_HOST}:{FLASK_PORT}
🎯 Guacamole: {GUAC_BASE}
📁 Scripts: {SCRIPTS_ROOT}
👥 Users: {', '.join(GUAC_USERS.keys())}
⏱️  Session Timeout: {SESSION_TIMEOUT}s
🔒 CORS Origins: {ALLOWED_ORIGINS}
🐛 Debug Mode: {FLASK_DEBUG}
📊 Performance Monitoring: Enabled
🔐 Security Logging: Enabled
============================================================
"""
            print(startup_info)
            app_logger.info("Server starting in DEBUG mode")
        else:
            app_logger.info(
                f"Server starting in PRODUCTION mode on {FLASK_HOST}:{FLASK_PORT}"
            )
            app_logger.info(f"Guacamole backend: {GUAC_BASE}")
            app_logger.info(f"Session timeout: {SESSION_TIMEOUT}s")

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

        # PRODUCTION CHANGES: Production warning
        if not FLASK_DEBUG:
            app_logger.warning(
                "🚀 Starting in production mode - use gunicorn for better performance"
            )

        # Start the server
        security_logger.info("SERVER_STARTING")
        app.socketio.run(
            app,
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=FLASK_DEBUG,
            use_reloader=FLASK_USE_RELOADER,
            ssl_context=SSL_CONTEXT,  # PRODUCTION CHANGE: SSL support
            allow_unsafe_werkzeug=True,
        )

    except KeyboardInterrupt:
        app_logger.info("🛑 Server shutdown requested by user")
        security_logger.info("SERVER_STOPPED_BY_USER")
    except Exception as e:
        app_logger.error(f"❌ Server startup error: {e}")
        security_logger.error(f"SERVER_STARTUP_ERROR: {e}")
        sys.exit(1)


# PRODUCTION CHANGES: WSGI application instance for gunicorn
application = create_wsgi_app()

if __name__ == "__main__":
    main()
