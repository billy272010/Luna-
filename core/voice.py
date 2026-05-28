"""
Interface vocale optionnelle (STT + TTS).
Si les dépendances ne sont pas installées, on tombe en mode texte.
"""
import threading
from typing import Optional

_tts_engine = None
_sr_available = False


def _init_tts():
    global _tts_engine
    try:
        import pyttsx3
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty("rate", 175)
        _tts_engine.setProperty("volume", 0.9)
        # Cherche une voix française
        voices = _tts_engine.getProperty("voices")
        for voice in voices:
            if "fr" in voice.id.lower() or "french" in voice.name.lower():
                _tts_engine.setProperty("voice", voice.id)
                break
    except Exception:
        _tts_engine = None


def _init_sr():
    global _sr_available
    try:
        import speech_recognition  # noqa: F401
        import pyaudio  # noqa: F401
        _sr_available = True
    except Exception:
        _sr_available = False


def is_voice_available() -> bool:
    return _tts_engine is not None


def is_stt_available() -> bool:
    return _sr_available


def speak(text: str) -> None:
    """Lit le texte à voix haute (non-bloquant)."""
    if _tts_engine is None:
        return

    def _run():
        try:
            _tts_engine.say(text)
            _tts_engine.runAndWait()
        except Exception:
            pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def listen(timeout: int = 5) -> Optional[str]:
    """Écoute le micro et retourne le texte reconnu."""
    if not _sr_available:
        return None
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        return recognizer.recognize_google(audio, language="fr-FR")
    except Exception:
        return None


# Initialisation au chargement du module
_init_tts()
_init_sr()
