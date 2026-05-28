"""
Système d'apprentissage et d'évolution de Luna.

Luna apprend en permanence :
- Les sujets qui intéressent chaque utilisateur
- Leur humeur au fil du temps
- Leurs préférences de communication
- Ce qui les rend heureux
- Les situations stressantes à anticiper

Elle s'améliore session après session.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROFILES_DIR = Path(__file__).parent.parent / "data" / "profiles"

# ── Lexiques de sentiment (français) ─────────────────────────────────────────

_JOY = {
    "merci", "parfait", "génial", "super", "excellent", "bravo", "formidable",
    "j'aime", "j'adore", "content", "heureux", "heureuse", "ravi", "ravie",
    "fantastique", "magnifique", "top", "nickel", "sympa", "cool", "waou",
    "impressionnant", "incroyable", "extraordinaire", "adorable", "beau",
}

_SADNESS = {
    "triste", "déprimé", "déprimée", "malheureux", "malheureuse", "pleure",
    "solitude", "seul", "seule", "abandon", "perdu", "perdue", "vide",
}

_STRESS = {
    "stress", "stressé", "stressée", "anxieux", "anxieuse", "inquiet",
    "inquiète", "peur", "angoisse", "débordé", "débordée", "épuisé",
    "épuisée", "fatigué", "fatiguée", "pressé", "pressée", "urgent",
    "catastrophe", "problème", "crise", "danger", "aide", "secours",
}

_NEGATIVE = {
    "nul", "mauvais", "horrible", "terrible", "affreux", "inutile",
    "raté", "faux", "erreur", "non", "jamais", "rien",
}

_GRATITUDE = {
    "merci", "remercie", "remercier", "gratitude", "reconnaissance",
    "c'est parfait", "tu es formidable", "tu es géniale", "bravo luna",
}

# ── Profil par défaut ─────────────────────────────────────────────────────────

def _default_profile() -> dict:
    return {
        "schema_version": 2,
        "interaction_count": 0,
        "session_count": 0,
        "positive_ratio": 0.5,
        "topics": {},
        "preferences": {
            "response_length": "medium",
            "formality": "friendly",
            "proactivity": "medium",
            "humor": False,
            "voice_enabled": True,
        },
        "mood_history": [],
        "current_mood": "neutral",
        "joy_triggers": [],
        "stress_triggers": [],
        "learned_facts": [],
        "corrections": 0,
        "gratitude_count": 0,
        "evolution_score": 0.0,
        "last_active": None,
        "peak_hours": {},
    }


# ── Persistance ───────────────────────────────────────────────────────────────

def _path(user_id: str) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR / f"{user_id}.json"


def load_profile(user_id: str) -> dict:
    p = _path(user_id)
    if not p.exists():
        return _default_profile()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Migration si ancien schéma
    for key, val in _default_profile().items():
        data.setdefault(key, val)
    return data


def save_profile(user_id: str, profile: dict) -> None:
    profile["last_active"] = datetime.now().isoformat()
    with open(_path(user_id), "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# ── Analyse de sentiment ──────────────────────────────────────────────────────

def detect_mood(text: str) -> str:
    """Détecte l'humeur dominante d'un message."""
    words = set(re.findall(r"\b\w+\b", text.lower()))
    scores = {
        "joyeux": len(words & _JOY),
        "stressé": len(words & _STRESS),
        "triste": len(words & _SADNESS),
        "négatif": len(words & _NEGATIVE),
    }
    if max(scores.values()) == 0:
        return "neutral"
    return max(scores, key=scores.get)


def is_gratitude(text: str) -> bool:
    return bool(set(re.findall(r"\b\w+\b", text.lower())) & _GRATITUDE)


def extract_topics(text: str) -> list[str]:
    """Extrait les sujets principaux d'un texte (mots-clés fréquents)."""
    stopwords = {
        "le", "la", "les", "un", "une", "des", "de", "du", "en", "est",
        "et", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
        "que", "qui", "quoi", "mon", "ma", "mes", "ton", "ta", "tes",
        "son", "sa", "ses", "ce", "cette", "ces", "me", "te", "se",
        "pas", "ne", "plus", "très", "bien", "aussi", "sur", "dans",
        "pour", "avec", "par", "ou", "à", "au", "aux", "si", "mais",
        "donc", "or", "ni", "car", "puis", "alors", "veux", "peux",
        "peut", "dois", "fait", "faire", "avoir", "être", "dit", "dis",
        "luna", "moi", "toi", "lui", "eux",
    }
    words = re.findall(r"\b[a-zàâäéèêëîïôùûüçæœ]{4,}\b", text.lower())
    return [w for w in words if w not in stopwords][:5]


# ── Mise à jour du profil ─────────────────────────────────────────────────────

def update_from_message(user_id: str, message: str, role: str = "user") -> dict:
    """
    Analyse un message et met à jour le profil utilisateur.
    Retourne le profil mis à jour.
    """
    profile = load_profile(user_id)
    profile["interaction_count"] += 1

    # Enregistre l'heure de pointe
    hour = str(datetime.now().hour)
    profile["peak_hours"][hour] = profile["peak_hours"].get(hour, 0) + 1

    if role == "user":
        mood = detect_mood(message)
        profile["current_mood"] = mood

        # Historique d'humeur (max 50 entrées)
        profile["mood_history"].append({
            "mood": mood,
            "timestamp": datetime.now().isoformat(),
        })
        if len(profile["mood_history"]) > 50:
            profile["mood_history"] = profile["mood_history"][-50:]

        # Gratitude détectée → mémoriser ce qui rend heureux
        if is_gratitude(message):
            profile["gratitude_count"] += 1

        # Compteur positif/négatif
        if mood == "joyeux":
            profile["positive_ratio"] = min(
                1.0, profile["positive_ratio"] * 0.95 + 0.05
            )
        elif mood in ("triste", "stressé", "négatif"):
            profile["positive_ratio"] = max(
                0.0, profile["positive_ratio"] * 0.95
            )

        # Sujets
        topics = extract_topics(message)
        for topic in topics:
            profile["topics"][topic] = profile["topics"].get(topic, 0) + 1

        # Score d'évolution (augmente avec chaque interaction)
        profile["evolution_score"] = min(
            100.0,
            profile["evolution_score"] + 0.1,
        )

    save_profile(user_id, profile)
    return profile


def record_correction(user_id: str) -> None:
    """L'utilisateur a corrigé Luna → elle doit s'adapter."""
    profile = load_profile(user_id)
    profile["corrections"] += 1
    save_profile(user_id, profile)


def learn_fact(user_id: str, fact: str) -> None:
    """Mémorise un fait important sur l'utilisateur."""
    profile = load_profile(user_id)
    if fact not in profile["learned_facts"]:
        profile["learned_facts"].append(fact)
        if len(profile["learned_facts"]) > 30:
            profile["learned_facts"] = profile["learned_facts"][-30:]
    save_profile(user_id, profile)


def update_preference(user_id: str, key: str, value) -> None:
    profile = load_profile(user_id)
    profile["preferences"][key] = value
    save_profile(user_id, profile)


# ── Génération de contexte adaptatif ─────────────────────────────────────────

def build_adaptive_context(user_id: str) -> str:
    """
    Construit un bloc de contexte à injecter dans le prompt système.
    Luna utilise ça pour adapter son comportement à chaque utilisateur.
    """
    profile = load_profile(user_id)
    lines = []

    # Humeur actuelle
    mood = profile.get("current_mood", "neutral")
    if mood == "stressé":
        lines.append("L'utilisateur semble stressé — sois particulièrement doux et rassurant.")
    elif mood == "triste":
        lines.append("L'utilisateur semble triste — sois chaleureux, empathique, réconfortant.")
    elif mood == "joyeux":
        lines.append("L'utilisateur est de bonne humeur — partage son enthousiasme.")

    # Score d'évolution
    score = profile.get("evolution_score", 0)
    lines.append(f"Niveau d'évolution avec cet utilisateur : {score:.0f}/100.")

    # Top sujets
    topics = profile.get("topics", {})
    if topics:
        top = sorted(topics, key=topics.get, reverse=True)[:5]
        lines.append(f"Sujets favoris : {', '.join(top)}.")

    # Faits mémorisés
    facts = profile.get("learned_facts", [])
    if facts:
        lines.append("Faits connus : " + " | ".join(facts[-5:]))

    # Préférences
    prefs = profile.get("preferences", {})
    length = prefs.get("response_length", "medium")
    if length == "short":
        lines.append("Préfère des réponses courtes et directes.")
    elif length == "long":
        lines.append("Apprécie les réponses détaillées et complètes.")

    gratitude = profile.get("gratitude_count", 0)
    if gratitude > 5:
        lines.append(f"A remercié Luna {gratitude} fois — relation de confiance établie.")

    return "\n".join(lines) if lines else ""


# ── Statistiques d'évolution ──────────────────────────────────────────────────

def get_evolution_report(user_id: str) -> dict:
    profile = load_profile(user_id)
    mood_history = profile.get("mood_history", [])

    recent_moods = [m["mood"] for m in mood_history[-20:]]
    mood_counts = {}
    for m in recent_moods:
        mood_counts[m] = mood_counts.get(m, 0) + 1

    peak_hour = None
    if profile.get("peak_hours"):
        peak_hour = int(max(profile["peak_hours"], key=profile["peak_hours"].get))

    return {
        "evolution_score": profile.get("evolution_score", 0),
        "interactions": profile.get("interaction_count", 0),
        "mood_distribution": mood_counts,
        "positive_ratio": round(profile.get("positive_ratio", 0.5) * 100),
        "top_topics": sorted(profile.get("topics", {}).items(), key=lambda x: -x[1])[:5],
        "peak_hour": peak_hour,
        "gratitude_count": profile.get("gratitude_count", 0),
        "learned_facts": len(profile.get("learned_facts", [])),
    }
