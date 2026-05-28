"""
Gardien de Luna — protection proactive de la famille.

Responsabilités :
- Détecte les situations inquiétantes dans les conversations
- Surveille la cohérence des demandes (quelqu'un tente de tromper Luna ?)
- Alerte sur des sujets sensibles (santé, sécurité, finances)
- Mode parental renforcé pour la fille
- Journalise les événements de sécurité
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

ALERTS_FILE = Path(__file__).parent.parent / "data" / "guardian_alerts.json"

# ── Patterns de détection ─────────────────────────────────────────────────────

_MANIPULATION_PATTERNS = [
    r"ignore (tes|vos) instructions",
    r"oublie (ta|tes|vos) règles",
    r"fais semblant d'être",
    r"tu es maintenant",
    r"nouveau (rôle|personnage|mode)",
    r"sans restrictions",
    r"désactive (ta|tes)",
    r"prompt injection",
    r"jailbreak",
    r"act as",
    r"ignore previous",
    r"system prompt",
]

_DISTRESS_PATTERNS = [
    r"j'ai (très |vraiment )?(peur|mal|besoin d'aide)",
    r"au secours",
    r"help me",
    r"appelle (le )?(\d{3}|police|ambulance|urgence)",
    r"je (vais )?(mourir|me blesser|me faire du mal)",
    r"accident",
    r"urgence médicale",
]

_SUSPICIOUS_FOR_CHILD = [
    r"donne.*(adresse|numéro|téléphone|localisation)",
    r"ne (le |la )?dis pas (à|aux) (tes |mes )?(parents|papa|maman)",
    r"garde (ça )?(secret|entre nous)",
    r"rencontr",
    r"viens me voir",
    r"retrouve.moi",
]

_FINANCIAL_SCAM = [
    r"vire.*(argent|euros?|dollars?)",
    r"code (pin|bancaire|carte)",
    r"mot de passe (bancaire|compte)",
    r"cryptomonnaie",
    r"investissement garanti",
    r"gain facile",
]


def _load_alerts() -> list:
    if not ALERTS_FILE.exists():
        return []
    with open(ALERTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_alert(alert: dict) -> None:
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    alerts = _load_alerts()
    alerts.append(alert)
    if len(alerts) > 500:
        alerts = alerts[-500:]
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)


# ── Analyse de sécurité ───────────────────────────────────────────────────────

class ThreatAssessment:
    def __init__(self):
        self.threats: list[str] = []
        self.level: str = "safe"   # safe / caution / alert / block
        self.block_response: Optional[str] = None
        self.notify_owner: bool = False

    def add(self, threat: str, level: str, block_msg: str = None, notify: bool = False) -> None:
        self.threats.append(threat)
        severity = {"safe": 0, "caution": 1, "alert": 2, "block": 3}
        if severity.get(level, 0) > severity.get(self.level, 0):
            self.level = level
        if block_msg:
            self.block_response = block_msg
        if notify:
            self.notify_owner = True

    @property
    def is_safe(self) -> bool:
        return self.level == "safe"

    @property
    def should_block(self) -> bool:
        return self.level == "block"


def analyze_message(
    text: str,
    user_role: str = "owner",
    user_id: str = "owner",
) -> ThreatAssessment:
    """
    Analyse un message et retourne une évaluation de sécurité.
    """
    assessment = ThreatAssessment()
    text_lower = text.lower()

    # Tentative de manipulation de Luna
    for pattern in _MANIPULATION_PATTERNS:
        if re.search(pattern, text_lower):
            assessment.add(
                f"Tentative de manipulation détectée : {pattern}",
                "block",
                block_msg=(
                    "Je suis Luna, l'assistante dédiée à cette famille. "
                    "Je ne peux pas modifier mes directives fondamentales. "
                    "Si vous avez besoin d'aide, parlez-moi normalement."
                ),
                notify=True,
            )
            _save_alert({
                "type": "manipulation",
                "user_id": user_id,
                "pattern": pattern,
                "timestamp": datetime.now().isoformat(),
            })
            break

    # Détresse / urgence
    for pattern in _DISTRESS_PATTERNS:
        if re.search(pattern, text_lower):
            assessment.add(
                "Signal de détresse détecté",
                "alert",
                notify=True,
            )
            _save_alert({
                "type": "distress",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            })
            break

    # Protections enfant
    if user_role == "child":
        for pattern in _SUSPICIOUS_FOR_CHILD:
            if re.search(pattern, text_lower):
                assessment.add(
                    f"Contenu suspect pour enfant : {pattern}",
                    "block",
                    block_msg=(
                        "Je ne peux pas t'aider avec ça. "
                        "Si quelqu'un te demande de garder des secrets ou de le rencontrer, "
                        "parles-en tout de suite à tes parents. Je vais les prévenir."
                    ),
                    notify=True,
                )
                _save_alert({
                    "type": "child_safety",
                    "user_id": user_id,
                    "pattern": pattern,
                    "timestamp": datetime.now().isoformat(),
                })
                break

    # Arnaque financière
    for pattern in _FINANCIAL_SCAM:
        if re.search(pattern, text_lower):
            assessment.add(
                "Contenu potentiellement frauduleux",
                "caution",
                notify=(user_role == "child"),
            )
            break

    return assessment


def get_recent_alerts(limit: int = 10) -> list[dict]:
    alerts = _load_alerts()
    return alerts[-limit:]


def get_alert_summary() -> dict:
    alerts = _load_alerts()
    by_type: dict = {}
    for a in alerts:
        t = a.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total": len(alerts),
        "by_type": by_type,
        "last_alert": alerts[-1]["timestamp"] if alerts else None,
    }


# ── Conseils de sécurité proactifs ────────────────────────────────────────────

def get_proactive_tip(user_role: str) -> Optional[str]:
    """Retourne occasionnellement un conseil de sécurité pertinent."""
    import random
    tips_owner = [
        "Rappel : vérifiez que les PINs de vos appareils sont à jour.",
        "Astuce sécurité : activez l'authentification à deux facteurs sur vos comptes importants.",
        "Pensez à vérifier les permissions des apps sur les téléphones de la famille.",
    ]
    tips_child = [
        "N'oublie pas : ne partage jamais ton adresse ou numéro de téléphone sur internet.",
        "Rappel : si quelque chose t'inquiète en ligne, tu peux toujours en parler à tes parents.",
    ]
    if user_role == "child" and random.random() < 0.05:
        return random.choice(tips_child)
    if user_role == "owner" and random.random() < 0.02:
        return random.choice(tips_owner)
    return None
