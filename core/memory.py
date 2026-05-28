"""
Mémoire persistante par utilisateur.
Stocke l'historique des conversations et les notes longue durée.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List

CONVERSATIONS_DIR = Path(__file__).parent.parent / "data" / "conversations"


def _user_file(user_id: str) -> Path:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    return CONVERSATIONS_DIR / f"{user_id}.json"


def _load_data(user_id: str) -> dict:
    path = _user_file(user_id)
    if not path.exists():
        return {"messages": [], "notes": [], "session_count": 0}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(user_id: str, data: dict) -> None:
    with open(_user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_history(user_id: str, max_messages: int = 20) -> List[dict]:
    """Retourne les derniers messages pour le contexte Claude."""
    data = _load_data(user_id)
    messages = data["messages"]
    return messages[-max_messages:] if len(messages) > max_messages else messages


def add_message(user_id: str, role: str, content: str) -> None:
    data = _load_data(user_id)
    data["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })
    # Garde max 200 messages par utilisateur
    if len(data["messages"]) > 200:
        data["messages"] = data["messages"][-200:]
    _save_data(user_id, data)


def add_note(user_id: str, note: str) -> None:
    """Note longue durée (rappel, préférence, info importante)."""
    data = _load_data(user_id)
    data["notes"].append({
        "content": note,
        "timestamp": datetime.now().isoformat(),
    })
    _save_data(user_id, data)


def get_notes(user_id: str) -> List[dict]:
    return _load_data(user_id).get("notes", [])


def clear_history(user_id: str) -> None:
    data = _load_data(user_id)
    data["messages"] = []
    _save_data(user_id, data)


def increment_session(user_id: str) -> int:
    data = _load_data(user_id)
    data["session_count"] = data.get("session_count", 0) + 1
    _save_data(user_id, data)
    return data["session_count"]
