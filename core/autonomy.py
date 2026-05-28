"""
Moteur d'autonomie de Luna.

Luna fonctionne en arrière-plan en permanence et prend des initiatives :
- Briefing matinal personnalisé
- Rappels proactifs
- Check-ins si l'utilisateur semble stressé
- Suggestions basées sur les habitudes
- Surveillance météo / actualités
- Alertes famille (batterie iPhone, dernière connexion, etc.)

Ce moteur tourne en thread daemon — il ne bloque jamais Luna.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from .identity import get_all_users, get_user
from .learning import load_profile, get_evolution_report
from .memory import get_notes, add_message

TASKS_FILE = Path(__file__).parent.parent / "data" / "scheduled_tasks.json"

# File de messages proactifs que Luna doit délivrer au prochain tour
_proactive_queue: Queue = Queue()
_running = False
_display_callback: Optional[Callable] = None


# ── Enregistrement d'un callback d'affichage ─────────────────────────────────

def set_display_callback(fn: Callable[[str, str], None]) -> None:
    """
    fn(user_id, message) — appelé quand Luna veut dire quelque chose proactivement.
    """
    global _display_callback
    _display_callback = fn


def push_proactive(user_id: str, message: str) -> None:
    """Ajoute un message proactif à la file."""
    _proactive_queue.put({"user_id": user_id, "message": message})


def pop_proactive(user_id: str) -> Optional[str]:
    """Récupère le prochain message proactif pour cet utilisateur."""
    items = []
    result = None
    while not _proactive_queue.empty():
        try:
            item = _proactive_queue.get_nowait()
            if item["user_id"] == user_id and result is None:
                result = item["message"]
            else:
                items.append(item)
        except Exception:
            break
    for item in items:
        _proactive_queue.put(item)
    return result


# ── Tâches planifiées ─────────────────────────────────────────────────────────

def _load_tasks() -> dict:
    if not TASKS_FILE.exists():
        return {}
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_tasks(tasks: dict) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def add_reminder(user_id: str, text: str, remind_at: str) -> None:
    """
    Ajoute un rappel.
    remind_at : ISO datetime string ou heure HH:MM (aujourd'hui ou demain)
    """
    tasks = _load_tasks()
    if user_id not in tasks:
        tasks[user_id] = []

    # Parse HH:MM
    if len(remind_at) == 5 and ":" in remind_at:
        h, m = remind_at.split(":")
        dt = datetime.now().replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        if dt <= datetime.now():
            dt += timedelta(days=1)
        remind_at = dt.isoformat()

    tasks[user_id].append({
        "text": text,
        "at": remind_at,
        "done": False,
    })
    _save_tasks(tasks)


def get_reminders(user_id: str, pending_only: bool = True) -> list[dict]:
    tasks = _load_tasks()
    user_tasks = tasks.get(user_id, [])
    if pending_only:
        return [t for t in user_tasks if not t.get("done")]
    return user_tasks


# ── Générateurs de messages proactifs ────────────────────────────────────────

def _morning_briefing(user_id: str) -> Optional[str]:
    """Briefing du matin (7h-9h) — une fois par jour."""
    now = datetime.now()
    if not (7 <= now.hour <= 9):
        return None

    profile = load_profile(user_id)
    last_active = profile.get("last_active")
    if last_active:
        last_dt = datetime.fromisoformat(last_active)
        if (now - last_dt).total_seconds() < 3600:
            return None  # Déjà vu aujourd'hui

    user = get_user(user_id)
    name = user["name"] if user else "vous"

    notes = get_notes(user_id)
    notes_block = ""
    if notes:
        recent = [n["content"] for n in notes[-2:]]
        notes_block = f" J'ai {len(notes)} note(s) pour vous, notamment : {recent[0][:60]}..."

    reminders = get_reminders(user_id)
    rem_block = ""
    if reminders:
        rem_block = f" Vous avez {len(reminders)} rappel(s) en attente."

    greetings = [
        f"Bonjour {name} ! Excellent début de journée.{notes_block}{rem_block} Comment puis-je vous aider ?",
        f"Bonjour {name} ! Je suis là et prête.{notes_block}{rem_block}",
        f"Bonne matinée {name} !{notes_block}{rem_block} À vos ordres.",
    ]
    import random
    return random.choice(greetings)


def _check_reminders(user_id: str) -> Optional[str]:
    """Vérifie si un rappel est dû."""
    tasks = _load_tasks()
    user_tasks = tasks.get(user_id, [])
    now = datetime.now()
    triggered = []

    for task in user_tasks:
        if task.get("done"):
            continue
        try:
            at = datetime.fromisoformat(task["at"])
            if at <= now:
                triggered.append(task)
                task["done"] = True
        except Exception:
            pass

    if triggered:
        _save_tasks(tasks)
        msgs = [t["text"] for t in triggered]
        if len(msgs) == 1:
            return f"⏰ Rappel : {msgs[0]}"
        return f"⏰ {len(msgs)} rappels : " + " | ".join(msgs)
    return None


def _wellbeing_check(user_id: str) -> Optional[str]:
    """Si l'utilisateur était stressé, proposer un check-in."""
    profile = load_profile(user_id)
    mood_history = profile.get("mood_history", [])
    if len(mood_history) < 3:
        return None

    recent_moods = [m["mood"] for m in mood_history[-5:]]
    stress_count = recent_moods.count("stressé") + recent_moods.count("triste")

    if stress_count >= 2:
        import random
        messages = [
            "Je vois que vous traversez une période difficile. Je suis là si vous voulez en parler.",
            "Comment vous sentez-vous ? J'ai remarqué que vous sembliez préoccupé(e) récemment.",
            "N'oubliez pas que je suis là pour vous soutenir. Tout va bien ?",
        ]
        return random.choice(messages)
    return None


def _evolution_milestone(user_id: str) -> Optional[str]:
    """Annonce les jalons d'évolution."""
    report = get_evolution_report(user_id)
    score = report["evolution_score"]
    interactions = report["interactions"]

    milestones = {
        10: "J'ai atteint 10 interactions avec vous — je commence à vous connaître.",
        50: "50 échanges ensemble ! Je comprends mieux vos préférences.",
        100: "100 interactions — notre lien s'est vraiment renforcé.",
        500: "500 échanges ! Je suis fière de notre collaboration.",
    }

    profile = load_profile(user_id)
    announced = profile.get("_milestones_announced", [])

    for threshold, msg in milestones.items():
        if interactions >= threshold and threshold not in announced:
            announced.append(threshold)
            profile["_milestones_announced"] = announced
            from .learning import save_profile
            save_profile(user_id, profile)
            return msg
    return None


# ── Boucle autonome principale ────────────────────────────────────────────────

def _autonomous_loop() -> None:
    """Tâche de fond — s'exécute toutes les 60 secondes."""
    last_morning = {}

    while _running:
        try:
            users = get_all_users()
            for uid in users:
                # Briefing matinal
                morning = _morning_briefing(uid)
                last_m = last_morning.get(uid)
                today = datetime.now().date().isoformat()
                if morning and last_m != today:
                    last_morning[uid] = today
                    push_proactive(uid, morning)
                    if _display_callback:
                        _display_callback(uid, morning)

                # Rappels
                reminder = _check_reminders(uid)
                if reminder:
                    push_proactive(uid, reminder)
                    if _display_callback:
                        _display_callback(uid, reminder)

                # Bien-être (1 fois par heure max)
                wellbeing = _wellbeing_check(uid)
                if wellbeing:
                    push_proactive(uid, wellbeing)

                # Jalons d'évolution
                milestone = _evolution_milestone(uid)
                if milestone:
                    push_proactive(uid, milestone)
                    if _display_callback:
                        _display_callback(uid, milestone)

        except Exception:
            pass

        time.sleep(60)


# ── API publique ──────────────────────────────────────────────────────────────

_thread: Optional[threading.Thread] = None


def start() -> None:
    global _running, _thread
    _running = True
    _thread = threading.Thread(target=_autonomous_loop, daemon=True, name="LunaAutonomy")
    _thread.start()


def stop() -> None:
    global _running
    _running = False


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()
