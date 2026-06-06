from __future__ import annotations

import datetime as _dt

from tts import speak


def tell_time() -> None:
    now = _dt.datetime.now().strftime("%I:%M %p").lstrip("0")
    speak(f"It is {now}")


def tell_joke() -> None:
    try:
        import pyjokes  # type: ignore
        speak(pyjokes.get_joke())
    except Exception:
        speak("I could not fetch a joke right now.")
