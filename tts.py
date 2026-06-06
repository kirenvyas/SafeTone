from __future__ import annotations

import logging
import os
import queue
import threading
from typing import Optional

from config import CFG

log = logging.getLogger(__name__)

_tts_queue: queue.Queue = queue.Queue()
_speaking_event = threading.Event()
_started_lock = threading.Lock()
_tts_thread: Optional[threading.Thread] = None
_started = False
_SENTINEL = object()


def _co_initialize():
    if os.name != "nt":
        return None
    try:
        import pythoncom  # type: ignore
        pythoncom.CoInitialize()
        return pythoncom
    except Exception:
        log.exception("TTS COM initialisation failed.")
        return None


def _co_uninitialize(pythoncom_mod):
    if pythoncom_mod is None:
        return
    try:
        pythoncom_mod.CoUninitialize()
    except Exception:
        pass


def _create_engine():
    import pyttsx3  # type: ignore

    try:
        engine = pyttsx3.init("sapi5")
        log.info("TTS engine initialised with driver 'sapi5'.")
    except Exception:
        engine = pyttsx3.init()
        log.info("TTS engine initialised with default driver.")

    engine.setProperty("rate", CFG.tts_rate)
    engine.setProperty("volume", CFG.tts_volume)

    try:
        voices = engine.getProperty("voices") or []
        if voices:
            engine.setProperty("voice", voices[0].id)
    except Exception:
        log.exception("TTS voice selection failed; using default voice.")

    return engine


def _speak_once(text: str) -> bool:
    pythoncom_mod = _co_initialize()
    engine = None
    try:
        engine = _create_engine()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        log.exception("TTS runtime error while speaking: %r", text)
        return False
    finally:
        try:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
        finally:
            _co_uninitialize(pythoncom_mod)


def _tts_worker() -> None:
    while True:
        try:
            item = _tts_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if item is _SENTINEL:
            _tts_queue.task_done()
            break

        text = str(item).strip()

        try:
            if text:
                _speaking_event.set()
                log.info("TTS speaking: %s", text)

                ok = _speak_once(text)
                if not ok:
                    log.warning("TTS first attempt failed. Retrying once: %s", text)
                    _speak_once(text)

        finally:
            _speaking_event.clear()
            _tts_queue.task_done()


def _ensure_started() -> None:
    global _started, _tts_thread
    with _started_lock:
        if _started:
            return
        _started = True
        _tts_thread = threading.Thread(target=_tts_worker, name="TTSWorker", daemon=True)
        _tts_thread.start()


def speak(text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        return
    _ensure_started()
    log.info("TTS request queued: %s", text)
    _speaking_event.set()
    _tts_queue.put(text)


def speak_wait(text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        return
    speak(text)
    _tts_queue.join()


def is_speaking() -> bool:
    return _speaking_event.is_set() or not _tts_queue.empty()


def shutdown_tts() -> None:
    global _started, _tts_thread
    if not _started:
        return
    _tts_queue.put(_SENTINEL)
    if _tts_thread is not None:
        _tts_thread.join(timeout=3)
    _tts_thread = None
    _started = False