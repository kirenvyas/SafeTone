from __future__ import annotations

import datetime
import logging
import threading
import time
import wave
from pathlib import Path
from tkinter import messagebox
from typing import Optional, Tuple

import numpy as np

from config import CFG
from database_manager import get_super_admin, initialize_database, login_user, register_user
from logger import setup_logging
from music import MusicPlayer
from routing import CommandRouter
from tts import speak, is_speaking
from voice_key import _TEMP_WAV, VoiceKey

try:
    import customtkinter as ctk  # type: ignore
except Exception:
    ctk = None

setup_logging()
log = logging.getLogger(__name__)

if ctk is not None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

_vk = VoiceKey()

C = {
    "bg": "#0f1117",
    "card": "#1a1d2e",
    "input": "#252840",
    "accent": "#4f8ef7",
    "accent2": "#7c5cbf",
    "text": "#e8eaf6",
    "dim": "#9e9eb3",
    "success": "#2ecc71",
    "danger": "#e74c3c",
    "warn": "#f39c12",
}


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def validate_registration_data(name: str, email: str, password: str, confirm: str, contact: str, has_voice: bool) -> \
Optional[str]:
    if not all([name.strip(), email.strip(), password, confirm, contact.strip()]):
        return "All fields are required."
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Enter a valid email address."
    if password != confirm:
        return "Passwords do not match."
    if len(password) < 6:
        return "Password must be at least 6 characters."
    if not contact.isdigit() or len(contact) < 7:
        return "Contact must be digits only (min. 7)."
    if not has_voice:
        return "Please record your voice profile first."
    return None


def authorize_voice_for_command(
        vk: VoiceKey,
        logged_in_user: dict,
        super_admin_user: Optional[dict],
        wav_path: str,
) -> Tuple[bool, str, float]:
    username = logged_in_user["name"]
    matched, score, info = vk.verify_file(username, wav_path)
    if matched:
        return True, f"LOGGED_IN_USER | {info}", score

    if (
            super_admin_user
            and super_admin_user.get("name")
            and super_admin_user["name"].lower() != username.lower()
            and vk.profile_exists(super_admin_user["name"])
    ):
        sa_matched, sa_score, sa_info = vk.verify_file(super_admin_user["name"], wav_path)
        if sa_matched:
            return True, f"SUPER_ADMIN_OVERRIDE | {sa_info}", sa_score

    return False, info, score


def _record_command() -> Optional[str]:
    try:
        import sounddevice as sd  # type: ignore
    except Exception:
        log.exception("sounddevice import failed.")
        time.sleep(1)
        return None

    try:
        audio: np.ndarray = sd.rec(
            int(CFG.command_duration * CFG.sample_rate), samplerate=CFG.sample_rate, channels=1, dtype="float32"
        )
        sd.wait()
        audio = audio.flatten()
    except Exception:
        log.exception("sounddevice recording failed.")
        time.sleep(1)
        return None

    rms = float(np.sqrt(np.mean(audio.astype("float64") ** 2)))
    if rms < CFG.silence_rms_threshold:
        return None

    try:
        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(_TEMP_WAV), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(CFG.sample_rate)
            wf.writeframes(pcm16.tobytes())
        return str(_TEMP_WAV)
    except Exception:
        log.exception("Failed to write temp WAV.")
        return None


def _transcribe(wav_path: str) -> str:
    try:
        import speech_recognition as sr  # type: ignore
    except Exception:
        log.exception("speech_recognition import failed.")
        return ""

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio).lower().strip()
    except Exception:
        return ""


if ctk is None:
    class VoiceAssistantApp:  # type: ignore[override]
        def __init__(self) -> None:
            raise RuntimeError("customtkinter is required to run this application.")
else:
    def _font(size: int, weight: str = "normal") -> ctk.CTkFont:
        return ctk.CTkFont(size=size, weight=weight)


    def _mono(size: int) -> ctk.CTkFont:
        return ctk.CTkFont(family="Consolas", size=size)


    class VoiceAssistantApp(ctk.CTk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Voice Assistant — Secure Edition")
            self.geometry("760x660")
            self.minsize(700, 580)
            self.configure(fg_color=C["bg"])

            self._logged_in_user: Optional[dict] = None
            self._enrolled_voice_path: Optional[str] = None
            self._music_player: Optional[MusicPlayer] = None
            self._router: Optional[CommandRouter] = None
            self._stop_event = threading.Event()
            self._shutdown_lock = threading.Lock()
            self._build_auth_screen()

        def on_close(self) -> None:
            self._stop_assistant(say_goodbye=False)
            self.destroy()

        def _build_auth_screen(self) -> None:
            for w in self.winfo_children():
                w.destroy()

            hdr = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=0, height=76)
            hdr.pack(fill="x")
            hdr.pack_propagate(False)
            ctk.CTkLabel(hdr, text="Voice Assistant", font=_font(26, "bold"), text_color=C["accent"]).pack(side="left",
                                                                                                           padx=28)
            ctk.CTkLabel(hdr, text="Register or login before starting", font=_font(13), text_color=C["dim"]).pack(
                side="left")

            self._tabs = ctk.CTkTabview(
                self,
                fg_color=C["card"],
                segmented_button_fg_color=C["bg"],
                segmented_button_selected_color=C["accent"],
                segmented_button_selected_hover_color="#3a7ce0",
                text_color=C["text"],
            )
            self._tabs.pack(fill="both", expand=True, padx=24, pady=18)
            self._tabs.add("Login")
            self._tabs.add("Register")
            self._build_login_tab()
            self._build_register_tab()

        def _build_login_tab(self) -> None:
            tab = self._tabs.tab("Login")
            ctk.CTkLabel(tab, text="Welcome Back", font=_font(20, "bold"), text_color=C["text"]).pack(pady=(22, 4))
            ctk.CTkLabel(tab, text="Login is required before the assistant starts.", font=_font(12),
                         text_color=C["dim"]).pack(pady=(0, 18))

            for label, attr, placeholder, secret in (
                    ("Full Name", "_login_name", "e.g. John Smith", False),
                    ("Contact Number", "_login_contact", "e.g. 9876543210", False),
                    ("Password", "_login_password", "Your password", True),
            ):
                ctk.CTkLabel(tab, text=label, text_color=C["dim"], anchor="w").pack(fill="x", padx=44)
                entry = ctk.CTkEntry(
                    tab,
                    placeholder_text=placeholder,
                    show="*" if secret else "",
                    fg_color=C["input"],
                    border_color=C["accent"],
                    text_color=C["text"],
                    height=40,
                )
                entry.pack(fill="x", padx=44, pady=(2, 12))
                setattr(self, attr, entry)

            self._login_btn = ctk.CTkButton(
                tab,
                text="Login",
                fg_color=C["accent"],
                hover_color="#3a7ce0",
                font=_font(14, "bold"),
                height=44,
                command=self._on_login_click,
            )
            self._login_btn.pack(fill="x", padx=44, pady=4)
            self._login_msg = ctk.CTkLabel(tab, text="", font=_font(12), text_color=C["danger"])
            self._login_msg.pack(pady=4)

        def _build_register_tab(self) -> None:
            tab = self._tabs.tab("Register")
            frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            frame.pack(fill="both", expand=True)

            ctk.CTkLabel(frame, text="Create Account", font=_font(20, "bold"), text_color=C["text"]).pack(pady=(14, 2))
            ctk.CTkLabel(frame, text="First registered user becomes Super Admin.", font=_font(12),
                         text_color=C["dim"]).pack(pady=(0, 14))

            for label, attr, placeholder, secret in (
                    ("Full Name *", "_reg_name", "Your full name", False),
                    ("Email Address *", "_reg_email", "your@email.com", False),
                    ("Password *", "_reg_password", "Min. 6 characters", True),
                    ("Confirm Password *", "_reg_confirm", "Repeat your password", True),
                    ("Contact Number *", "_reg_contact", "Digits only e.g. 9876543210", False),
            ):
                ctk.CTkLabel(frame, text=label, text_color=C["dim"], anchor="w").pack(fill="x", padx=30)
                entry = ctk.CTkEntry(
                    frame,
                    placeholder_text=placeholder,
                    show="*" if secret else "",
                    fg_color=C["input"],
                    border_color=C["accent"],
                    text_color=C["text"],
                    height=38,
                )
                entry.pack(fill="x", padx=30, pady=(2, 10))
                setattr(self, attr, entry)

            vcard = ctk.CTkFrame(frame, fg_color=C["bg"], corner_radius=12)
            vcard.pack(fill="x", padx=30, pady=4)
            ctk.CTkLabel(vcard, text="Voice Enrollment (Required)", font=_font(13, "bold"), text_color=C["warn"]).pack(
                pady=(12, 4))
            ctk.CTkLabel(vcard, text="Records a 10-second continuous audio clip for your voice profile.",
                         font=_font(11), text_color=C["dim"]).pack(pady=(0, 10))
            self._record_btn = ctk.CTkButton(vcard, text="Start Voice Registration", fg_color=C["accent2"],
                                             hover_color="#6a4dab", font=_font(13, "bold"), height=44,
                                             command=self._on_record_click)
            self._record_btn.pack(fill="x", padx=20, pady=(0, 8))
            self._enroll_label = ctk.CTkLabel(vcard, text="No voice profile recorded yet.", font=_font(11),
                                              text_color=C["dim"])
            self._enroll_label.pack(pady=(0, 12))

            self._submit_btn = ctk.CTkButton(frame, text="Create Account", fg_color="#555566", hover_color="#555566",
                                             font=_font(14, "bold"), height=44, state="disabled",
                                             command=self._on_register_click)
            self._submit_btn.pack(fill="x", padx=30, pady=(14, 4))
            self._reg_msg = ctk.CTkLabel(frame, text="", font=_font(12), text_color=C["danger"])
            self._reg_msg.pack(pady=4)

        def _on_login_click(self) -> None:
            name = self._login_name.get().strip()
            contact = self._login_contact.get().strip()
            password = self._login_password.get()
            self._login_btn.configure(state="disabled", text="Checking ...")
            self._login_msg.configure(text="")

            def _worker() -> None:
                result = login_user(name, contact, password)
                self.after(0, lambda: self._finish_login(result))

            threading.Thread(target=_worker, daemon=True, name="LoginWorker").start()

        def _finish_login(self, result: dict) -> None:
            self._login_btn.configure(state="normal", text="Login")
            if result["success"]:
                self._logged_in_user = result["user"]
                self._build_assistant_screen()
            else:
                self._login_msg.configure(text=result["message"], text_color=C["danger"])

        def _on_record_click(self) -> None:
            name = self._reg_name.get().strip()
            if not name:
                messagebox.showwarning("Name Required", "Enter your name before recording.")
                return

            self._record_btn.configure(state="disabled", text="Recording in progress...")
            self._enroll_label.configure(text="Loading voice model and recording clips...", text_color=C["warn"])
            self._submit_btn.configure(state="disabled", fg_color="#555566")
            self._enrolled_voice_path = None

            def _progress(msg: str) -> None:
                self.after(0, lambda: self._enroll_label.configure(text=msg, text_color=C["warn"]))

            def _worker() -> None:
                success = _vk.register(name, progress_callback=_progress)
                self.after(0, lambda: self._finish_enroll(name, success))

            threading.Thread(target=_worker, daemon=True, name="EnrollWorker").start()

        def _finish_enroll(self, name: str, success: bool) -> None:
            if success:
                self._enrolled_voice_path = _vk.get_profile_path(name)
                info = _vk.get_profile_info(name) or {}
                self._enroll_label.configure(
                    text=f"Voice profile ready! SpeechBrain threshold={_fmt(info.get('threshold'))}",
                    text_color=C["success"],
                )
                self._record_btn.configure(state="normal", text="Re-record Voice Profile", fg_color="#2d6a4f",
                                           hover_color="#1b4332")
                self._submit_btn.configure(state="normal", fg_color=C["success"], hover_color="#27ae60")
            else:
                error = _vk.get_last_error() or "Recording failed. Please speak louder and closer to the microphone."
                self._enroll_label.configure(text=error, text_color=C["danger"])
                self._record_btn.configure(state="normal", text="Start Voice Registration", fg_color=C["accent2"],
                                           hover_color="#6a4dab")

        def _on_register_click(self) -> None:
            name = self._reg_name.get().strip()
            email = self._reg_email.get().strip()
            password = self._reg_password.get()
            confirm = self._reg_confirm.get()
            contact = self._reg_contact.get().strip()
            error = validate_registration_data(name, email, password, confirm, contact, bool(self._enrolled_voice_path))
            if error:
                self._reg_msg.configure(text=error, text_color=C["danger"])
                return

            self._submit_btn.configure(state="disabled", text="Creating account ...")
            voice_path = self._enrolled_voice_path or ""

            def _worker() -> None:
                result = register_user(name, email, password, contact, voice_path)
                self.after(0, lambda: self._finish_register(result, name, contact))

            threading.Thread(target=_worker, daemon=True, name="RegisterWorker").start()

        def _finish_register(self, result: dict, name: str, contact: str) -> None:
            self._submit_btn.configure(state="normal", text="Create Account")
            if result["success"]:
                messagebox.showinfo("Registration Successful",
                                    f"{result['message']}\n\nNow log in to start the assistant.")
                self._tabs.set("Login")
                self._login_name.delete(0, "end")
                self._login_name.insert(0, name)
                self._login_contact.delete(0, "end")
                self._login_contact.insert(0, contact)
                self._reg_msg.configure(text="", text_color=C["text"])
            else:
                self._reg_msg.configure(text=result["message"], text_color=C["danger"])

        def _build_assistant_screen(self) -> None:
            for w in self.winfo_children():
                w.destroy()
            user = self._logged_in_user or {}

            hdr = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=0, height=72)
            hdr.pack(fill="x")
            hdr.pack_propagate(False)
            ctk.CTkLabel(hdr, text="Voice Assistant", font=_font(22, "bold"), text_color=C["accent"]).pack(side="left",
                                                                                                           padx=24)
            ctk.CTkLabel(hdr, text="Command voice must match logged-in user or Super Admin", font=_font(11),
                         text_color=C["success"]).pack(side="left", padx=12)

            ubox = ctk.CTkFrame(hdr, fg_color="transparent")
            ubox.pack(side="right", padx=20)
            ctk.CTkLabel(ubox, text=user.get("name", ""), font=_font(13, "bold"), text_color=C["text"]).pack(anchor="e")
            ctk.CTkLabel(ubox, text=user.get("role", ""), font=_font(11),
                         text_color=C["warn"] if user.get("role") == "Super Admin" else C["dim"]).pack(anchor="e")

            banner = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14)
            banner.pack(fill="x", padx=20, pady=(14, 6))
            ctk.CTkLabel(banner, text=f"Welcome, {user.get('name', '')}!", font=_font(22, "bold"),
                         text_color=C["success"]).pack(pady=(16, 4))
            ctk.CTkLabel(banner,
                         text="Each command is verified against the logged-in user first, then Super Admin if needed.",
                         font=_font(12), text_color=C["dim"]).pack(pady=(0, 14))

            sbar = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14)
            sbar.pack(fill="x", padx=20, pady=4)
            self._status_label = ctk.CTkLabel(sbar, text="Initialising ...", font=_font(13, "bold"),
                                              text_color=C["text"])
            self._status_label.pack(side="left", padx=20, pady=13)

            ctk.CTkLabel(self, text="Activity Log", font=_font(12, "bold"), text_color=C["dim"], anchor="w").pack(
                fill="x", padx=24, pady=(8, 2))
            self._log_box = ctk.CTkTextbox(self, fg_color=C["card"], text_color=C["text"], font=_mono(12),
                                           corner_radius=12, state="disabled")
            self._log_box.pack(fill="both", expand=True, padx=20, pady=(0, 8))

            hint = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=12)
            hint.pack(fill="x", padx=20, pady=(0, 4))
            ctk.CTkLabel(hint,
                         text="Say: play music, pause, resume, next, previous, shuffle, volume up, search, open YouTube, what time, tell me a joke, exit",
                         font=_font(11), text_color=C["dim"], wraplength=720).pack(pady=9, padx=14)
            ctk.CTkButton(self, text="Logout", fg_color="#383850", hover_color=C["danger"], font=_font(12), height=34,
                          command=self._on_logout_click).pack(pady=(0, 14))
            self._start_assistant()

        def _ui_log(self, msg: str) -> None:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {msg}\n"

            def _append() -> None:
                try:
                    self._log_box.configure(state="normal")
                    self._log_box.insert("end", line)
                    self._log_box.see("end")
                    self._log_box.configure(state="disabled")
                except Exception:
                    pass

            try:
                self.after(0, _append)
            except RuntimeError:
                pass

        def _ui_status(self, text: str, color: str = "") -> None:
            if self._stop_event.is_set():
                return
            try:
                self.after(0, lambda: self._status_label.configure(text=text, text_color=color or C["text"]))
            except RuntimeError:
                pass

        def _start_assistant(self) -> None:
            self._stop_event.clear()

            def _setup() -> None:
                try:
                    self._music_player = MusicPlayer(CFG.music_folder)
                    self._router = CommandRouter(self._music_player)
                    source_folder = str(self._music_player.source_folder or CFG.music_folder)
                    self._ui_log(f"Music player ready. Folder: {source_folder}. Songs: {len(self._music_player.songs)}")
                except Exception:
                    log.exception("Music player initialisation failed.")
                    self._router = CommandRouter(None)
                    self._ui_log("Music player failed. Music commands disabled.")

                if not _vk.ensure_ready():
                    err = _vk.get_last_error() or "Unknown voice model error."
                    self._ui_log(f"Voice model unavailable: {err}")
                    self._ui_status("Voice model unavailable", C["danger"])
                    speak("Voice verification model is not available. Please fix dependencies and restart.")
                    return

                self._ui_status("Listening ...", C["success"])
                speak(f"Welcome {self._logged_in_user['name']}. I am ready.")
                self._voice_loop()

            threading.Thread(target=_setup, daemon=True, name="AssistantSetup").start()

        def _stop_assistant(self, say_goodbye: bool = True) -> None:
            with self._shutdown_lock:
                if self._stop_event.is_set():
                    return
                self._stop_event.set()
            if say_goodbye:
                speak("Goodbye!")
            time.sleep(0.3)
            if self._music_player:
                try:
                    self._music_player.shutdown()
                except Exception:
                    log.exception("MusicPlayer shutdown raised.")
                self._music_player = None
            self._router = None

        def _voice_loop(self) -> None:
            user = self._logged_in_user or {}
            username = user.get("name", "")
            super_admin = get_super_admin()
            while not self._stop_event.is_set():
                try:
                    while is_speaking():
                        if self._stop_event.is_set():
                            break
                        time.sleep(0.1)

                    if self._stop_event.is_set():
                        break

                    self._ui_status("Listening ...", C["success"])
                    wav_path = _record_command()
                    if self._stop_event.is_set():
                        break
                    if wav_path is None:
                        continue

                    if not _vk.profile_exists(username):
                        self._ui_log("No voice profile for logged-in user. Commands denied.")
                        speak("No voice profile found for the logged in user.")
                        time.sleep(1)
                        continue

                    self._ui_status("Verifying voice ...", C["warn"])
                    authorised, info, _ = authorize_voice_for_command(_vk, user, super_admin, wav_path)
                    if not authorised:
                        self._ui_log(f"DENIED — {info}")
                        speak("User voice not authenticated")
                        continue

                    self._ui_status("Transcribing ...", C["accent"])
                    text = _transcribe(wav_path)
                    if not text:
                        self._ui_log(f"Verified ({info}) — speech unclear.")
                        continue

                    self._ui_log(f'Verified ({info}) → "{text}"')
                    self._ui_status(f"Running: {text}", C["accent"])
                    if self._router is None:
                        self._ui_log("Command router unavailable.")
                        continue
                    if self._router.handle(text):
                        self._ui_log("Exit command received.")
                        self._stop_event.set()
                        break
                except Exception:
                    if self._stop_event.is_set():
                        break
                    log.exception("Unhandled exception in voice loop.")
                    self._ui_log("Internal error — retrying ...")
                    time.sleep(1)

        def _on_logout_click(self) -> None:
            if not messagebox.askyesno("Logout", "Are you sure you want to log out?"):
                return
            self._stop_assistant(say_goodbye=True)
            self._logged_in_user = None
            self._enrolled_voice_path = None
            self._stop_event = threading.Event()
            self._build_auth_screen()

if __name__ == "__main__":
    initialize_database()
    if ctk is None:
        raise RuntimeError("customtkinter is required. Install dependencies from requirements.txt")
    app = VoiceAssistantApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
