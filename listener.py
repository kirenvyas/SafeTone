from __future__ import annotations

import concurrent.futures
import logging

from config import CFG
from tts import is_speaking

log = logging.getLogger(__name__)


class Listener:
    def __init__(self) -> None:
        self.recognizer = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._sr = None
        try:
            import speech_recognition as sr  # type: ignore
            self._sr = sr
            self.recognizer = sr.Recognizer()
            self._calibrate()
        except Exception:
            log.exception("speech_recognition is not available.")

    def _calibrate(self) -> None:
        if self._sr is None or self.recognizer is None:
            return
        try:
            with self._sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=CFG.ambient_duration)
        except Exception:
            log.exception("Ambient calibration failed.")

    def listen(self) -> str:
        if is_speaking() or self._sr is None or self.recognizer is None:
            return ""
        try:
            with self._sr.Microphone() as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=CFG.listen_timeout,
                    phrase_time_limit=CFG.phrase_time_limit,
                )
        except Exception:
            return ""

        try:
            future = self.executor.submit(self.recognizer.recognize_google, audio)
            text = future.result(timeout=6)
            return text.lower().strip()
        except Exception:
            return ""

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)
