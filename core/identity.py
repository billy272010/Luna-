"""
Gestion des utilisateurs et de l'authentification.
"""
import json
import hashlib
import os
from pathlib import Path
from typing import Optional

USERS_FILE = Path(__file__).parent.parent / "data" / "users" / "users.json"


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users: dict) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def is_setup_done() -> bool:
    users = load_users()
    return bool(users.get("owner"))


def create_user(user_id: str, name: str, role: str, pin: str, aliases: list[str] = None) -> None:
    users = load_users()
    users[user_id] = {
        "id": user_id,
        "name": name,
        "role": role,
        "pin_hash": _hash_pin(pin),
        "aliases": aliases or [name.lower()],
        "preferences": {},
    }
    save_users(users)


def update_user_preference(user_id: str, key: str, value) -> None:
    users = load_users()
    if user_id in users:
        users[user_id]["preferences"][key] = value
        save_users(users)


def authenticate(user_id: str, pin: str) -> bool:
    users = load_users()
    user = users.get(user_id)
    if not user:
        return False
    return user["pin_hash"] == _hash_pin(pin)


def get_user(user_id: str) -> Optional[dict]:
    users = load_users()
    return users.get(user_id)


def get_all_users() -> dict:
    return load_users()


def identify_by_name(name: str) -> Optional[str]:
    """Retourne l'ID utilisateur depuis un prénom ou alias."""
    users = load_users()
    name_lower = name.lower().strip()
    for uid, user in users.items():
        if name_lower == user["name"].lower():
            return uid
        if name_lower in [a.lower() for a in user.get("aliases", [])]:
            return uid
    return None
