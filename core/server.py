"""
Serveur HTTP local de Luna.
Permet aux iPhones de communiquer avec Luna via le réseau WiFi local.

Endpoints :
  POST /command        — L'iPhone déclenche une action sur Luna
  GET  /status         — Vérifie que Luna est en ligne
  GET  /pending/<uid>  — L'iPhone récupère les commandes en attente
  POST /location       — L'iPhone envoie sa position GPS
  POST /siri           — L'iPhone envoie une commande vocale Siri → Luna
"""

import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

# File de commandes en attente par user_id
_pending: dict[str, list] = {}
# Callback appelé quand l'iPhone envoie un message à Luna
_message_callback: Optional[Callable] = None
# Dernières positions GPS
_locations: dict[str, dict] = {}

LUNA_VERSION = "1.0"


def set_message_callback(fn: Callable) -> None:
    """Enregistre la fonction appelée quand l'iPhone parle à Luna."""
    global _message_callback
    _message_callback = fn


def push_command(user_id: str, command: dict) -> None:
    """Met une commande en file d'attente pour un iPhone."""
    if user_id not in _pending:
        _pending[user_id] = []
    _pending[user_id].append({**command, "queued_at": datetime.now().isoformat()})


def get_last_location(user_id: str) -> Optional[dict]:
    return _locations.get(user_id)


class _Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Silence les logs HTTP

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/status":
            self._send_json({
                "luna": "online",
                "version": LUNA_VERSION,
                "timestamp": datetime.now().isoformat(),
            })

        elif path.startswith("/pending/"):
            user_id = path.split("/pending/")[-1].strip("/")
            commands = _pending.pop(user_id, [])
            self._send_json({"commands": commands, "count": len(commands)})

        else:
            self._send_json({"error": "Route inconnue"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/command":
            # L'iPhone déclenche une action sur Luna
            action = body.get("action", "")
            user_id = body.get("user_id", "unknown")
            params = body.get("params", {})

            if _message_callback and action == "message":
                text = params.get("text", "")
                if text:
                    threading.Thread(
                        target=_message_callback,
                        args=(user_id, text),
                        daemon=True,
                    ).start()
            self._send_json({"ok": True, "received": action})

        elif path == "/location":
            # L'iPhone envoie sa position GPS
            user_id = body.get("user_id", "unknown")
            _locations[user_id] = {
                "lat": body.get("lat"),
                "lon": body.get("lon"),
                "accuracy": body.get("accuracy"),
                "timestamp": datetime.now().isoformat(),
                "address": body.get("address"),
            }
            self._send_json({"ok": True})

        elif path == "/siri":
            # Siri Shortcut → Luna : commande vocale
            user_id = body.get("user_id", "owner")
            text = body.get("text", "")
            if text and _message_callback:
                threading.Thread(
                    target=_message_callback,
                    args=(user_id, f"[Siri] {text}"),
                    daemon=True,
                ).start()
            self._send_json({"ok": True, "echo": text})

        else:
            self._send_json({"error": "Route inconnue"}, 404)


class LunaServer:
    def __init__(self, port: int = 7777):
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._server = HTTPServer(("0.0.0.0", self.port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
