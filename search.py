from __future__ import annotations

import logging
import webbrowser
from urllib.parse import quote_plus

from tts import speak
from utilities import fuzzy_match

log = logging.getLogger(__name__)

SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chat.openai.com",
}


def open_website(name: str) -> bool:
    match = fuzzy_match(name, list(SITES.keys()), 0.6)
    if not match:
        return False
    try:
        speak(f"Opening {match}")
        webbrowser.open(SITES[match])
        return True
    except Exception:
        log.exception("Failed to open website: %s", match)
        speak("I could not open that website.")
        return False


def search_google(query: str) -> bool:
    query = query.strip()
    if not query:
        speak("Please say what you want me to search.")
        return False
    try:
        speak(f"Searching {query}")
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
        return True
    except Exception:
        log.exception("Google search failed for query: %s", query)
        speak("I could not perform that search.")
        return False
