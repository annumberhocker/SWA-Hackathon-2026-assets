"""HTTP control server — exposes POST /control to start/stop the simulator.

Runs as a lightweight sidecar process so the Streamlit dashboard can
start and stop the producer via an HTTP call instead of managing a subprocess
directly (which Streamlit's execution model makes difficult).
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from dotenv import load_dotenv

_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV)

BIND    = os.getenv("SIMULATOR_CONTROL_BIND", "127.0.0.1")
PORT    = int(os.getenv("SIMULATOR_CONTROL_PORT", "8090"))

# Shared mutable state passed to the producer thread
_state: dict = {"running": False, "sent": 0, "errors": 0}
_state_lock   = threading.Lock()


class ControlHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence access log noise
        pass

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/status":
            with _state_lock:
                self._send_json(200, dict(_state))
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/control":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode()) if length else {}
        action = body.get("action", "").lower()

        with _state_lock:
            if action == "start":
                _state["running"] = True
                self._send_json(200, {"status": "started"})
            elif action == "stop":
                _state["running"] = False
                self._send_json(200, {"status": "stopped"})
            else:
                self._send_json(400, {"error": f"unknown action: {action}"})


def get_state() -> dict:
    with _state_lock:
        return dict(_state)


def run(autostart: bool = False):
    """Start the control server. Blocks until KeyboardInterrupt."""
    if autostart or os.getenv("SIMULATOR_AUTOSTART", "").lower() in ("1", "true", "yes"):
        with _state_lock:
            _state["running"] = True
        print("Simulator autostart enabled — producer will begin immediately.")

    class _ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True

    server = _ReusableHTTPServer((BIND, PORT), ControlHandler)
    print(f"Simulator control server listening on http://{BIND}:{PORT}/control")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
