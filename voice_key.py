from __future__ import annotations

import importlib
import logging
import os
import shutil
import warnings
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf

log = logging.getLogger(__name__)

from config import CFG

SAMPLE_RATE = CFG.sample_rate
ENROLL_DURATION = CFG.enroll_duration
COMMAND_DURATION = CFG.command_duration
VOICE_MATCH_THRESHOLD = CFG.voice_match_threshold

_BASE_DIR = CFG.base_dir
_PROFILES_DIR = CFG.voiceprints_dir
_MODELS_DIR = CFG.pretrained_models_dir
_TEMP_WAV = CFG.base_dir / "temp_command.wav"


def _safe_name(username: str) -> str:
    return "".join(
        c for c in username.strip() if c.isalnum() or c in (" ", "_", "-")
    ).strip().replace(" ", "_").lower()


def _rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))


class VoiceKey:
    def __init__(
        self,
        profiles_dir: Optional[Path | str] = None,
        model_dir: Optional[Path | str] = None,
        threshold: float = VOICE_MATCH_THRESHOLD,
    ) -> None:
        self.base_dir = _BASE_DIR
        self.profiles_dir = Path(profiles_dir) if profiles_dir else _PROFILES_DIR
        self.model_dir = Path(model_dir) if model_dir else _MODELS_DIR
        self.threshold = float(threshold)

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self._verifier = None
        self._last_error: Optional[str] = None

        log.info(
            "VoiceKey initialised. profiles='%s' models='%s'",
            self.profiles_dir,
            self.model_dir,
        )

    def _user_dir(self, username: str) -> Path:
        return self.profiles_dir / _safe_name(username)

    def get_profile_path(self, username: str) -> str:
        return str(self._profile_path(username))

    def _profile_path(self, username: str) -> Path:
        return self._user_dir(username) / "enrollment.wav"

    def _record_audio(
            self,
            duration: float,
            prompt: str = "",
            progress_callback=None,
    ) -> Optional[np.ndarray]:
        if prompt:
            print(prompt)

        try:
            frames = int(max(duration, 0.2) * SAMPLE_RATE)
            audio = sd.rec(
                frames,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )

            if progress_callback:
                step_ms = 100
                total_ms = int(duration * 1000)
                elapsed = 0
                while elapsed < total_ms:
                    wait_ms = min(step_ms, total_ms - elapsed)
                    sd.sleep(wait_ms)
                    elapsed += wait_ms
                    progress_callback(min(elapsed / total_ms, 1.0))
                sd.wait()
            else:
                sd.wait()

            return np.asarray(audio, dtype=np.float32).flatten()
        except Exception:
            log.exception("Audio recording failed.")
            return None

    def _record_clip(self, duration: float) -> Optional[np.ndarray]:
        return self._record_audio(duration)

    def _patch_torchaudio(self) -> None:
        try:
            import torchaudio  # type: ignore

            if not hasattr(torchaudio, "list_audio_backends"):
                torchaudio.list_audio_backends = lambda: ["soundfile"]

            if not hasattr(torchaudio, "set_audio_backend"):
                def _set_audio_backend(_name: str) -> None:
                    return None

                torchaudio.set_audio_backend = _set_audio_backend

            if not hasattr(torchaudio, "get_audio_backend"):
                def _get_audio_backend() -> str:
                    return "soundfile"

                torchaudio.get_audio_backend = _get_audio_backend

        except Exception:
            pass

    def _create_verifier(self):
        self._patch_torchaudio()

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*set_audio_backend.*deprecated.*",
                category=UserWarning,
            )

            try:
                module = importlib.import_module("speechbrain.inference.speaker")
                SpeakerRecognition = module.SpeakerRecognition
            except ModuleNotFoundError:
                module = importlib.import_module("speechbrain.pretrained")
                SpeakerRecognition = module.SpeakerRecognition

        return SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(self.model_dir),
            run_opts={"device": "cpu"},
        )

    def get_last_error(self):
        """Return the last internal error message."""
        return getattr(self, "_last_error", None)

    def ensure_ready(self) -> bool:
        if self._verifier is not None:
            return True

        try:
            log.info("Loading SpeechBrain speaker verification model...")
            self._verifier = self._create_verifier()
            self._last_error = None
            log.info("SpeechBrain model loaded successfully.")
            return True
        except Exception as exc:
            self._last_error = str(exc)
            log.exception("Speaker verification model failed to load.")
            return False

    @property
    def verifier(self):
        if self._verifier is None:
            ok = self.ensure_ready()
            if not ok:
                raise RuntimeError(
                    self._last_error or "Voice verifier could not be loaded."
                )
        return self._verifier

    def _write_wav(self, path: Path, audio: np.ndarray) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(path), audio, SAMPLE_RATE)
            return True
        except Exception:
            log.exception("Failed to write WAV file: %s", path)
            return False

    def register(self, username: str, progress_callback=None) -> bool:
        username = username.strip()
        if not username:
            log.warning("Registration rejected: empty username.")
            return False

        profile = self._profile_path(username)

        print(f"\n  {'─' * 60}")
        print(f"  VOICE REGISTRATION  ──  {username}")
        print(f"  {'─' * 60}")
        print(f"  Please speak clearly for {ENROLL_DURATION} seconds.")
        print("  Say a few natural sentences in a quiet room.")
        print("  Recording starts in 3... 2... 1... GO!\n")

        if progress_callback:
            progress_callback(0.0)

        if progress_callback:
            audio = self._record_audio(ENROLL_DURATION, progress_callback=progress_callback)
        else:
            audio = self._record_clip(ENROLL_DURATION)

        if audio is None:
            self._last_error = "Microphone recording failed. Is the mic connected?"
            print("  Error: microphone recording failed.")
            return False

        level = _rms(audio)
        if level < 1e-5:
            self._last_error = "No audio detected! Check Windows Privacy Settings (Microphone access) or check if mic is muted."
            log.warning("Registration failed for '%s': NO AUDIO DETECTED (rms=%.6f).", username, level)
            print("  Error: No audio detected.")
            return False
            
        if level < CFG.silence_rms_threshold:
            log.warning("Registration warning for '%s': audio very quiet (rms=%.6f).", username, level)

        if not self._write_wav(profile, audio):
            self._last_error = "Could not save voice profile."
            print("  Error: could not save voice profile.")
            return False

        if progress_callback:
            progress_callback(1.0)

        print(f"  Done! Your voice is saved as '{profile}'.\n")
        log.info("Registration completed for '%s' -> %s", username, profile)
        return True

    def verify_file(self, username: str, wav_path: str) -> Tuple[bool, float, str]:
        profile = self._profile_path(username)

        if not profile.exists():
            log.warning("verify_file: no profile for '%s'.", username)
            return False, 0.0, "no_profile"

        if not wav_path or not os.path.exists(wav_path):
            log.warning("verify_file: bad wav path for '%s': %s", username, wav_path)
            return False, 0.0, "bad_audio"

        if not self.ensure_ready():
            return False, 0.0, f"model_unavailable: {self._last_error}"

        try:
            score_tensor, _ = self.verifier.verify_files(str(profile), str(wav_path))
            score = float(score_tensor.item())
            matched = score >= self.threshold
            status = "MATCH" if matched else "NO MATCH"
            info = f"score={score:.2f} threshold={self.threshold:.2f} {status}"

            log.info(
                "verify_file '%s' score=%.3f threshold=%.2f -> %s",
                username,
                score,
                self.threshold,
                status,
            )
            print(
                f"  [VoiceKey]  {username:<18}  "
                f"score={score:>8.2f}  threshold={self.threshold:>7.2f}  {status}"
            )
            return matched, score, info

        except Exception:
            log.exception("verify_file scoring failed for '%s'.", username)
            return False, 0.0, "scoring_error"

    def verify(self, username: str, duration: float = 4.0, progress_callback=None) -> Tuple[bool, float, str]:
        print(f"\n  {'─' * 60}")
        print(f"  VOICE VERIFICATION  ──  {username}")
        print(f"  {'─' * 60}")

        if not self.profile_exists(username):
            print(f"  No profile found for '{username}'. Please register first.")
            return False, 0.0, "no_profile"

        print(f"  I'm listening, {username} — speak for {duration} seconds...")

        if progress_callback:
            audio = self._record_audio(duration, progress_callback=progress_callback)
        else:
            audio = self._record_clip(duration)

        if audio is None:
            return False, 0.0, "mic_error"

        if not self._write_wav(_TEMP_WAV, audio):
            return False, 0.0, "temp_write_error"

        try:
            matched, score, info = self.verify_file(username, str(_TEMP_WAV))
            print(f"\n  {'GRANTED' if matched else 'DENIED'}")
            print(f"  {info}")
            print(f"  {'─' * 60}\n")
            return matched, score, info
        finally:
            try:
                if _TEMP_WAV.exists():
                    _TEMP_WAV.unlink()
            except Exception:
                log.warning("Could not delete temp wav: %s", _TEMP_WAV)

    def identify(self, duration: float = 4.0) -> str:
        profiles = self.list_profiles()
        if not profiles:
            print("  No profiles registered yet.")
            return "Unknown"

        if not self.ensure_ready():
            return "Unknown"

        print(f"\n  {'─' * 60}")
        print("  VOICE IDENTIFICATION")
        print(f"  {'─' * 60}")
        print("  Say a few words so I can recognise you...")

        audio = self._record_clip(duration)
        if audio is None:
            return "Unknown"

        if not self._write_wav(_TEMP_WAV, audio):
            return "Unknown"

        best_score = float("-inf")
        best_name = "Unknown"

        try:
            for name in profiles:
                profile = self._profile_path(name)
                try:
                    score_tensor, _ = self.verifier.verify_files(str(profile), str(_TEMP_WAV))
                    score = float(score_tensor.item())
                    if score > best_score:
                        best_score = score
                        best_name = name
                except Exception:
                    log.exception("identify: scoring failed for '%s'.", name)

            if best_score >= self.threshold:
                print(
                    f"\n  Identified: {best_name}  "
                    f"score={best_score:.2f}  threshold={self.threshold:.2f}"
                )
                print(f"  {'─' * 60}\n")
                return best_name

            print("  Scores too low -> Unknown.")
            return "Unknown"
        finally:
            try:
                if _TEMP_WAV.exists():
                    _TEMP_WAV.unlink()
            except Exception:
                log.warning("Could not delete temp wav: %s", _TEMP_WAV)

    def check_duplicate_file(self, wav_path: str, skip_username: str = "") -> Optional[str]:
        if not wav_path or not os.path.exists(wav_path):
            return None

        if not self.ensure_ready():
            return None

        skip = _safe_name(skip_username)

        for name in self.list_profiles():
            if _safe_name(name) == skip:
                continue

            profile = self._profile_path(name)
            try:
                score_tensor, _ = self.verifier.verify_files(str(profile), str(wav_path))
                score = float(score_tensor.item())
                if score >= self.threshold:
                    return name
            except Exception:
                log.exception("Duplicate check failed for '%s'.", name)

        return None

    def delete_profile(self, username: str) -> bool:
        user_dir = self._user_dir(username)
        try:
            if user_dir.exists():
                shutil.rmtree(user_dir)
                return True
            return False
        except Exception:
            log.exception("Failed to delete profile for '%s'.", username)
            return False

    def list_profiles(self) -> list[str]:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        return sorted(
            p.name for p in self.profiles_dir.iterdir()
            if p.is_dir() and (p / "enrollment.wav").exists()
        )

    def profile_exists(self, username: str) -> bool:
        return self._profile_path(username).exists()

    def get_profile_info(self, username: str) -> Optional[dict]:
        if not self.profile_exists(username):
            return None

        return {
            "self_score": 1.0,
            "self_std": 0.0,
            "threshold": self.threshold,
            "gate_info": "SpeechBrain ECAPA-TDNN",
            "quality": "EXCELLENT",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vk = VoiceKey()
    print("\n" + "=" * 62)
    print("  VoiceKey —— SpeechBrain AI Authentication Demo")
    print("=" * 62)
    input("\n  Press ENTER to register a new user 'demo_user'...")
    vk.register("demo_user")
    input("\n  Press ENTER to verify (speak as yourself)...")
    vk.verify("demo_user")