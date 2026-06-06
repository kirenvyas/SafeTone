from __future__ import annotations

import logging
import os
import platform

from tts import speak

log = logging.getLogger(__name__)


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _press_key(key: str) -> bool:
    try:
        import pyautogui  # type: ignore
        pyautogui.press(key)
        return True
    except Exception:
        log.exception("pyautogui key press failed: %s", key)
        speak("System control is not available right now.")
        return False


def volume_up() -> bool:
    ok = _press_key("volumeup")
    if ok:
        speak("Volume increased")
    return ok


def volume_down() -> bool:
    ok = _press_key("volumedown")
    if ok:
        speak("Volume decreased")
    return ok


def volume_set(level: int) -> bool:
    try:
        level = max(0, min(int(level), 100))
    except Exception:
        speak("Invalid volume level")
        return False

    for _ in range(50):
        if not _press_key("volumedown"):
            return False
    for _ in range(level // 2):
        if not _press_key("volumeup"):
            return False
    speak(f"Volume set to {level}")
    return True


def _run_system_command(command: str, spoken: str) -> bool:
    if not _is_windows():
        log.warning("Skipping Windows-only system command on non-Windows OS: %s", command)
        speak(f"{spoken}. This command works only on Windows.")
        return False
    speak(spoken)
    return os.system(command) == 0


def shutdown() -> bool:
    return _run_system_command("shutdown /s /t 5", "Shutting down system")


def restart() -> bool:
    return _run_system_command("shutdown /r /t 5", "Restarting system")


def sleep() -> bool:
    return _run_system_command("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", "Putting system to sleep")
