from __future__ import annotations

from typing import Optional

from jokes_time import tell_joke, tell_time
from music import MusicPlayer
from search import open_website, search_google
from system_controls import restart, shutdown, sleep, volume_down, volume_up
from tts import speak


class CommandRouter:
    def __init__(self, music: Optional[MusicPlayer]) -> None:
        self.music = music

    def _music_cmd(self, action: str) -> None:
        if self.music is None:
            speak("Music player is not available right now.")
            return
        getattr(self.music, action)()

    def _music_action_from_phrase(self, phrase: str) -> Optional[str]:
        text = phrase.lower().strip()
        if not text:
            return None

        if text in ("play", "music", "play music","play songs"):
            return "play"
        if text in ("pause", "pause music", "hold music","pause song","pause songs"):
            return "pause"
        if text in ("resume", "resume music", "continue", "continue music", "unpause", "play again", "resume song"):
            return "resume"
        if text in (
            "next",
            "next song",
            "next track",
            "next music",
            "skip",
            "skip song",
            "play next",
            "play next song",
            "play next track",
        ):
            return "next"
        if text in (
            "previous",
            "previous song",
            "previous track",
            "last song",
            "go back",
            "play previous",
            "play previous song",
            "play previous track",
            "play last song",
        ):
            return "previous"
        if text in ("shuffle", "shuffle music", "random", "random song", "play random","shuffle song"):
            return "shuffle"
        if text in ("stop", "stop music", "stop playing", "stop the music"):
            return "stop"
        return None

    def handle(self, command: str) -> bool:
        cmd = command.lower().strip()
        if not cmd:
            speak("Please say a command.")
            return False

        if any(w in cmd for w in ("exit", "quit", "goodbye", "bye", "stop listening")):
            speak("Goodbye!")
            return True

        if any(p in cmd for p in ("what time", "what is time", "current time", "time now", "tell time", "clock", "tell me time")):
            tell_time()
            return False

        if any(p in cmd for p in ("joke", "funny", "make me laugh")):
            tell_joke()
            return False

        if "shutdown" in cmd and "music" not in cmd:
            shutdown()
            return True

        if "restart" in cmd and "music" not in cmd:
            restart()
            return True

        if cmd in ("sleep", "sleep mode", "go to sleep"):
            sleep()
            return False

        if any(p in cmd for p in ("volume up", "turn up", "louder")):
            volume_up()
            return False

        if any(p in cmd for p in ("volume down", "turn down", "quieter")):
            volume_down()
            return False

        music_action = self._music_action_from_phrase(cmd)
        if music_action is not None:
            self._music_cmd(music_action)
            return False

        if cmd.startswith("play "):
            query = cmd[5:].strip()
            if query.startswith("music "):
                query = query[6:].strip()

            music_action = self._music_action_from_phrase(query)
            if music_action is not None:
                self._music_cmd(music_action)
                return False

            if query == "":
                self._music_cmd("play")
                return False

            if self.music and self.music.play_by_name(query):
                return False
            if self.music is None:
                speak("Music player is not available.")
            else:
                speak(f"Sorry, I couldn't find a song matching {query}.")
            return False

        if cmd.startswith("open "):
            site = cmd.replace("open", "", 1).strip()
            if not open_website(site):
                search_google(site)
            return False

        if cmd.startswith("search ") or cmd.startswith("look up ") or cmd.startswith("google "):
            query = cmd.replace("search", "", 1).replace("look up", "", 1).replace("google", "", 1).strip()
            search_google(query)
            return False

        if any(cmd.startswith(prefix) for prefix in ("who is", "what is", "where is", "how to", "tell me about")):
            search_google(cmd)
            return False

        speak("I did not understand that. Please try again.")
        return False
