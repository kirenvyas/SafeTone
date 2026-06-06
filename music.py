from __future__ import annotations

import logging
import os
import random
import threading
from difflib import get_close_matches
from pathlib import Path
from typing import Iterable, Optional

from config import CFG
from tts import speak

log = logging.getLogger(__name__)


class _NullMusic:
    def load(self, path: str) -> None:
        return None

    def play(self) -> None:
        return None

    def pause(self) -> None:
        return None

    def unpause(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def get_busy(self) -> bool:
        return False


class _NullMixer:
    def __init__(self) -> None:
        self.music = _NullMusic()

    def init(self) -> None:
        return None

    def quit(self) -> None:
        return None


class MusicPlayer:
    def __init__(self, folder: str) -> None:
        self.requested_folder = str(folder or "")
        self.folder = self.requested_folder  # kept for compatibility with rest of project
        self.source_folder: Optional[Path] = None
        self.song_paths: list[Path] = []
        self.songs: list[str] = []
        self.index = 0
        self._playing = False
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self._mixer = _NullMixer()
        self.available = False

        self._load_songs()
        self._init_mixer()
        threading.Thread(target=self._watcher, daemon=True, name="MusicWatcher").start()

    def _init_mixer(self) -> None:
        try:
            import pygame  # type: ignore

            pygame.mixer.init()
            self._mixer = pygame.mixer
            self.available = True
            log.info(
                "pygame.mixer initialised. Songs found: %d. Source folder: %s",
                len(self.songs),
                self.source_folder if self.source_folder else "None",
            )
        except Exception:
            log.exception("pygame.mixer failed to initialise. Music commands will degrade gracefully.")
            self._mixer = _NullMixer()
            self.available = False

    def _normalise_folder(self, value: str) -> Optional[Path]:
        raw = str(value or "").strip().strip('"').strip("'")
        if not raw:
            return None
        expanded = os.path.expandvars(os.path.expanduser(raw))
        path = Path(expanded)
        if path.is_absolute():
            return path
        return (CFG.base_dir / path).resolve()

    def _candidate_folders(self) -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def _add(path: Optional[Path]) -> None:
            if path is None:
                return
            try:
                resolved = path.resolve(strict=False)
            except Exception:
                resolved = path
            key = str(resolved).lower()
            if key not in seen:
                seen.add(key)
                candidates.append(resolved)

        explicit = self._normalise_folder(self.requested_folder)
        env_folder = self._normalise_folder(os.environ.get("VOICE_ASSISTANT_MUSIC_FOLDER", ""))

        _add(explicit)
        _add(env_folder)
        _add((CFG.base_dir / "music"))
        _add((CFG.base_dir / "songs"))
        _add(Path.home() / "Music")

        return candidates

    def _iter_song_files(self, folder: Path) -> Iterable[Path]:
        try:
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in CFG.music_extensions:
                    yield path
        except Exception:
            log.exception("Failed while scanning music folder: %s", folder)

    def _display_name(self, path: Path) -> str:
        try:
            if self.source_folder is not None:
                rel = path.relative_to(self.source_folder)
                return rel.stem if len(rel.parts) == 1 else str(rel.with_suffix(""))
        except Exception:
            pass
        return path.stem

    def _rebuild_song_names(self) -> None:
        self.songs = [self._display_name(path) for path in self.song_paths]

    def _load_songs(self) -> None:
        self.song_paths = []
        self.songs = []
        checked: list[str] = []
        all_found: list[Path] = []

        for folder in self._candidate_folders():
            checked.append(str(folder))
            if not folder.exists() or not folder.is_dir():
                continue
            found = sorted(self._iter_song_files(folder), key=lambda p: str(p).lower())
            if not found:
                continue
            if self.source_folder is None:
                self.source_folder = folder
            all_found.extend(found)

        unique_paths: list[Path] = []
        seen: set[str] = set()
        for path in all_found:
            key = str(path.resolve(strict=False)).lower()
            if key not in seen:
                seen.add(key)
                unique_paths.append(path)

        self.song_paths = unique_paths
        self._rebuild_song_names()

        if not self.song_paths:
            log.warning("No songs found. Requested folder: %s | Checked folders: %s", self.requested_folder or "<empty>", ", ".join(checked))
        else:
            log.info(
                "Loaded %d songs. Requested folder: %s | Using source folder: %s",
                len(self.song_paths),
                self.requested_folder or "<empty>",
                self.source_folder,
            )

    def refresh_library(self) -> int:
        with self.lock:
            current_name = self.songs[self.index] if self.song_paths and 0 <= self.index < len(self.songs) else None
            self._load_songs()
            if not self.song_paths:
                self.index = 0
                self._playing = False
                return 0
            if current_name in self.songs:
                self.index = self.songs.index(current_name)
            else:
                self.index = min(self.index, len(self.song_paths) - 1)
            return len(self.song_paths)

    def _play_index(self, idx: int) -> None:
        if not self.available:
            self._playing = False
            return
        if not self.song_paths:
            self._playing = False
            return
        self.index = idx % len(self.song_paths)
        path = self.song_paths[self.index]
        try:
            self._mixer.music.load(str(path))
            self._mixer.music.play()
            self._playing = True
            log.info("Now playing: %s", path)
        except Exception:
            log.exception("Failed to play '%s'.", path)
            self._playing = False
            speak("I could not play that song.")

    def _watcher(self) -> None:
        while not self.stop_event.is_set():
            self.stop_event.wait(1)
            if self.stop_event.is_set():
                break
            with self.lock:
                if self._playing and not self._mixer.music.get_busy() and self.song_paths:
                    next_idx = (self.index + 1) % len(self.song_paths)
                    self._play_index(next_idx)

    @property
    def is_playing(self) -> bool:
        if not self.available:
            return False
        try:
            return self._playing and bool(self._mixer.music.get_busy())
        except Exception:
            return False

    def play(self) -> None:
        if not self.song_paths:
            loaded = self.refresh_library()
            if loaded == 0:
                speak("No songs found in the music folder.")
                return
        with self.lock:
            if self.is_playing:
                speak(f"Already playing {self.songs[self.index]}")
            else:
                self._play_index(self.index)
                if self._playing:
                    speak(f"Playing {self.songs[self.index]}")

    def pause(self) -> None:
        with self.lock:
            try:
                self._mixer.music.pause()
            except Exception:
                log.exception("Failed to pause music.")
            self._playing = False
        speak("Music paused.")

    def resume(self) -> None:
        with self.lock:
            try:
                self._mixer.music.unpause()
                self._playing = True
            except Exception:
                log.exception("Failed to resume music.")
                self._playing = False
        speak("Resuming music.")

    def stop(self) -> None:
        with self.lock:
            try:
                self._mixer.music.stop()
            except Exception:
                log.exception("Failed to stop music.")
            self._playing = False
        speak("Music stopped.")

    def next(self) -> None:
        if not self.song_paths:
            speak("No songs loaded.")
            return
        with self.lock:
            self._play_index((self.index + 1) % len(self.song_paths))
        if self._playing:
            speak(f"Next song: {self.songs[self.index]}")

    def previous(self) -> None:
        if not self.song_paths:
            speak("No songs loaded.")
            return
        with self.lock:
            self._play_index((self.index - 1) % len(self.song_paths))
        if self._playing:
            speak(f"Previous song: {self.songs[self.index]}")

    def shuffle(self) -> None:
        if not self.song_paths:
            speak("No songs loaded.")
            return
        with self.lock:
            library = list(zip(self.song_paths, self.songs))
            random.shuffle(library)
            self.song_paths, self.songs = map(list, zip(*library))
            self.index = 0
            self._play_index(self.index)
        if self._playing:
            speak(f"Shuffled. Playing {self.songs[self.index]}")

    def play_by_name(self, query: str) -> bool:
        if not self.song_paths:
            loaded = self.refresh_library()
            if loaded == 0:
                speak("No songs loaded.")
                return False
        names_normalised = [song.lower().replace("_", " ") for song in self.songs]
        clean_query = query.lower().strip().replace("_", " ")
        matches = get_close_matches(clean_query, names_normalised, n=1, cutoff=0.4)
        if not matches:
            return False
        idx = names_normalised.index(matches[0])
        with self.lock:
            self._play_index(idx)
        if self._playing:
            speak(f"Playing {self.songs[idx]}")
        return self._playing

    def shutdown(self) -> None:
        self.stop_event.set()
        try:
            self._mixer.quit()
        except Exception:
            pass
