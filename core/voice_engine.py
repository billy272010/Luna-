"""
Moteur vocal humain de Luna.

Hiérarchie :
  1. edge-tts   — voix neurale Microsoft (gratuit, aucune clé, qualité remarquable)
  2. ElevenLabs — voix premium (clé API dans .env)
  3. pyttsx3    — fallback offline

Voix françaises edge-tts recommandées :
  fr-FR-DeniseNeural   (femme, chaleureux)
  fr-FR-HenriNeural    (homme, professionnel)
  fr-FR-EloisaNeural   (femme, doux)
"""

import asyncio
import os
import platform
import subprocess
import tempfile
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

# ── Détection des moteurs disponibles ────────────────────────────────────────

_EDGE_AVAILABLE = False
_ELEVEN_AVAILABLE = False
_PYTTSX3_AVAILABLE = False

try:
    import edge_tts  # noqa: F401
    _EDGE_AVAILABLE = True
except ImportError:
    pass

try:
    from elevenlabs import ElevenLabs  # noqa: F401
    _ELEVEN_AVAILABLE = bool(os.getenv("ELEVENLABS_API_KEY"))
except ImportError:
    pass

try:
    import pyttsx3  # noqa: F401
    _PYTTSX3_AVAILABLE = True
except ImportError:
    pass

# ── Configuration des voix ────────────────────────────────────────────────────

VOICES = {
    "luna_female": "fr-FR-DeniseNeural",
    "luna_male": "fr-FR-HenriNeural",
    "luna_soft": "fr-FR-EloisaNeural",
}

DEFAULT_VOICE = os.getenv("LUNA_VOICE", VOICES["luna_female"])

# ── Lecture audio multiplateforme ─────────────────────────────────────────────

def _play_file(filepath: str) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["afplay", filepath], check=True, capture_output=True)
        elif system == "Windows":
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME)
        else:
            # Linux — essaie plusieurs lecteurs
            for cmd in [
                ["mpg123", "-q", filepath],
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", filepath],
                ["cvlc", "--play-and-exit", "--quiet", filepath],
            ]:
                if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                    subprocess.run(cmd, capture_output=True)
                    return
    except Exception:
        pass


# ── Edge TTS (neural, gratuit) ────────────────────────────────────────────────

async def _edge_generate(text: str, voice: str, output_path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _speak_edge(text: str, voice: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        asyncio.run(_edge_generate(text, voice, tmp))
        _play_file(tmp)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── ElevenLabs (premium) ──────────────────────────────────────────────────────

def _speak_elevenlabs(text: str, voice_id: str = None) -> None:
    from elevenlabs import ElevenLabs, VoiceSettings
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=vid,
        voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75),
        model_id="eleven_multilingual_v2",
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        for chunk in audio:
            f.write(chunk)
        tmp = f.name
    try:
        _play_file(tmp)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ── pyttsx3 (fallback offline) ────────────────────────────────────────────────

def _speak_pyttsx3(text: str) -> None:
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 0.95)
    for voice in engine.getProperty("voices"):
        if "fr" in voice.id.lower() or "french" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            break
    engine.say(text)
    engine.runAndWait()


# ── File de parole (non-bloquant) ─────────────────────────────────────────────

_speech_queue: Queue = Queue()
_worker_thread: Optional[threading.Thread] = None
_active = False


def _speech_worker() -> None:
    while _active:
        try:
            text, voice = _speech_queue.get(timeout=0.5)
            if not text:
                continue
            _do_speak(text, voice)
        except Empty:
            continue
        except Exception:
            pass


def _do_speak(text: str, voice: str) -> None:
    # Nettoie le markdown pour la voix
    clean = _clean_for_voice(text)
    if not clean.strip():
        return

    if _ELEVEN_AVAILABLE:
        _speak_elevenlabs(clean)
    elif _EDGE_AVAILABLE:
        _speak_edge(clean, voice)
    elif _PYTTSX3_AVAILABLE:
        _speak_pyttsx3(clean)


def _clean_for_voice(text: str) -> str:
    """Supprime markdown, URLs, emojis pour une lecture naturelle."""
    import re
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)   # gras/italique
    text = re.sub(r"`[^`]+`", "", text)                       # code inline
    text = re.sub(r"```[\s\S]*?```", "", text)                # blocs code
    text = re.sub(r"https?://\S+", "le lien", text)           # URLs
    text = re.sub(r"#+\s", "", text)                           # titres
    text = re.sub(r"[-•]\s", "", text)                         # puces
    text = re.sub(r"[^\x00-\x7FÀ-ɏḀ-ỿ\s.,!?;:'\"-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── API publique ──────────────────────────────────────────────────────────────

def start() -> None:
    """Démarre le worker vocal en arrière-plan."""
    global _worker_thread, _active
    if not is_available():
        return
    _active = True
    _worker_thread = threading.Thread(target=_speech_worker, daemon=True)
    _worker_thread.start()


def stop() -> None:
    global _active
    _active = False


def speak(text: str, voice: str = DEFAULT_VOICE, blocking: bool = False) -> None:
    """Met un texte en file de parole."""
    if not is_available():
        return
    if blocking:
        _do_speak(text, voice)
    else:
        _speech_queue.put((text, voice))


def speak_clear(text: str) -> None:
    """Vide la file puis parle immédiatement (interruption)."""
    while not _speech_queue.empty():
        try:
            _speech_queue.get_nowait()
        except Empty:
            break
    speak(text)


def is_available() -> bool:
    return _EDGE_AVAILABLE or _ELEVEN_AVAILABLE or _PYTTSX3_AVAILABLE


def get_engine_name() -> str:
    if _ELEVEN_AVAILABLE:
        return "ElevenLabs"
    if _EDGE_AVAILABLE:
        return "Edge TTS (Neural)"
    if _PYTTSX3_AVAILABLE:
        return "pyttsx3"
    return "Aucun"


def list_available_voices() -> list[str]:
    """Retourne les voix edge-tts françaises disponibles."""
    if not _EDGE_AVAILABLE:
        return []

    async def _get():
        voices = await edge_tts.list_voices()
        return [v["ShortName"] for v in voices if v.get("Locale", "").startswith("fr-")]

    try:
        return asyncio.run(_get())
    except Exception:
        return list(VOICES.values())
