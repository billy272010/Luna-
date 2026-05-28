"""
Intégration Apple Shortcuts + iOS.

3 méthodes de contrôle :
  1. macOS URL scheme  — shortcuts://run-shortcut?name=X  (si Luna tourne sur Mac)
  2. HTTP webhook      — POST vers l'iPhone via réseau local
  3. ntfy.sh           — notification push → déclenche un Raccourci iOS
"""

import json
import platform
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from core.permissions import has_permission

CONFIG_FILE = Path(__file__).parent.parent / "config" / "ios_config.json"


# ── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"server_port": 7777, "devices": {}, "shortcuts": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def register_device(user_id: str, ip: str, name: str = None) -> None:
    cfg = load_config()
    if user_id not in cfg["devices"]:
        cfg["devices"][user_id] = {}
    cfg["devices"][user_id]["ip"] = ip
    if name:
        cfg["devices"][user_id]["name"] = name
    save_config(cfg)


def set_ntfy_topic(topic: str) -> None:
    cfg = load_config()
    cfg["ntfy_topic"] = topic
    save_config(cfg)


# ── Envoi de commandes ────────────────────────────────────────────────────────

def _trigger_via_macos(shortcut_name: str) -> bool:
    """Déclenche un Raccourci sur le Mac (et donc iPhone si partagé iCloud)."""
    if platform.system() != "Darwin":
        return False
    encoded = urllib.parse.quote(shortcut_name)
    result = subprocess.run(
        ["open", f"shortcuts://run-shortcut?name={encoded}"],
        capture_output=True,
    )
    return result.returncode == 0


def _trigger_via_http(ip: str, shortcut_name: str, params: dict = None) -> dict:
    """
    POST vers l'iPhone sur le réseau local.
    Requiert le Raccourci 'Luna Serveur' installé sur l'iPhone
    (voir shortcuts_ios/Luna_Serveur.md pour les instructions).
    """
    url = f"http://{ip}:8765/command"
    payload = json.dumps({
        "shortcut": shortcut_name,
        "params": params or {},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read()
            return json.loads(body) if body else {"ok": True}
    except urllib.error.URLError as e:
        return {"error": f"Appareil inaccessible : {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _trigger_via_ntfy(topic: str, shortcut_name: str, params: dict = None,
                      server: str = "https://ntfy.sh") -> dict:
    """
    Envoie une notification ntfy.sh → l'app ntfy sur iPhone
    déclenche automatiquement un Raccourci via l'automation 'Notification reçue'.
    """
    if not topic:
        return {"error": "ntfy_topic non configuré"}
    message = json.dumps({"shortcut": shortcut_name, "params": params or {}})
    url = f"{server}/{topic}"
    try:
        req = urllib.request.Request(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": f"Luna → {shortcut_name}",
                "Tags": "robot",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"ok": True, "status": resp.status}
    except Exception as e:
        return {"error": str(e)}


def send_command(user_id: str, shortcut_id: str,
                 params: dict = None, current_user_role: str = "owner") -> dict:
    """
    Point d'entrée principal : envoie une commande iOS à l'appareil d'un utilisateur.
    Respecte les restrictions owner_only.
    """
    cfg = load_config()

    # Trouve le raccourci
    shortcut = next((s for s in cfg["shortcuts"] if s["id"] == shortcut_id), None)
    if not shortcut:
        return {"error": f"Raccourci '{shortcut_id}' inconnu"}

    # Vérifie les permissions
    if shortcut.get("owner_only") and not has_permission(current_user_role, "manage_users"):
        return {"error": "Accès refusé — commande réservée au propriétaire"}

    shortcut_name = shortcut["shortcut_name"]
    device = cfg.get("devices", {}).get(user_id, {})

    # Priorité : HTTP local > ntfy > macOS
    if device.get("ip"):
        result = _trigger_via_http(device["ip"], shortcut_name, params)
        if "error" not in result:
            return result

    ntfy_topic = cfg.get("ntfy_topic", "")
    if ntfy_topic:
        return _trigger_via_ntfy(ntfy_topic, shortcut_name, params,
                                 cfg.get("ntfy_server", "https://ntfy.sh"))

    if _trigger_via_macos(shortcut_name):
        return {"ok": True, "method": "macos"}

    return {"error": "Aucune méthode de communication disponible. "
                     "Configurez l'IP de l'iPhone ou un topic ntfy."}


def send_command_all(shortcut_id: str, params: dict = None,
                     current_user_role: str = "owner") -> dict:
    """Envoie la même commande à tous les appareils enregistrés."""
    cfg = load_config()
    results = {}
    for uid in cfg.get("devices", {}):
        results[uid] = send_command(uid, shortcut_id, params, current_user_role)
    return results


# ── Informations ─────────────────────────────────────────────────────────────

def list_shortcuts(current_user_role: str = "child") -> list:
    """Retourne les raccourcis disponibles pour le rôle donné."""
    cfg = load_config()
    is_owner = has_permission(current_user_role, "manage_users")
    return [
        s for s in cfg["shortcuts"]
        if not s.get("owner_only") or is_owner
    ]


def list_devices() -> dict:
    cfg = load_config()
    return cfg.get("devices", {})


def get_shortcut_by_id(shortcut_id: str) -> Optional[dict]:
    cfg = load_config()
    return next((s for s in cfg["shortcuts"] if s["id"] == shortcut_id), None)
