from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _app_root() -> Path:
    """
    In normal Python mode:
        project folder
    In PyInstaller frozen mode:
        folder containing the .exe
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    base_dir: Path = field(default_factory=_app_root)
    data_dir: Path = field(default_factory=_app_root)

    music_folder: str = field(
        default_factory=lambda: os.environ.get(
            "VOICE_ASSISTANT_MUSIC_FOLDER",
            r"D:\Music",
        )
    )

    listen_timeout: float = 4.0
    phrase_time_limit: float = 8.0
    ambient_duration: float = 1.0

    tts_rate: int = 180
    tts_volume: float = 1.0

    log_file: str = "assistant.log"
    database_name: str = "users.db"
    voiceprints_dir_name: str = "voiceprints"
    pretrained_dir_name: str = "pretrained_models"

    music_extensions: tuple[str, ...] = (".mp3", ".wav", ".ogg")
    fuzzy_threshold: float = 0.6
    voice_match_threshold: float = 0.25

    enroll_duration: int = 10
    command_duration: int = 5
    sample_rate: int = 16000
    silence_rms_threshold: float = 0.001

    @property
    def db_path(self) -> Path:
        return self.base_dir / self.database_name

    @property
    def voiceprints_dir(self) -> Path:
        path = self.base_dir / self.voiceprints_dir_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def pretrained_models_dir(self) -> Path:
        path = self.base_dir / self.pretrained_dir_name
        path.mkdir(parents=True, exist_ok=True)
        return path


CFG = Config()