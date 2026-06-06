# SafeTone: Secure Command‑Based Windows Voice Assistant

SafeTone is a desktop voice assistant for Windows built with Python.  It combines a graphical login system, mandatory voice enrollment, speaker verification, natural‑language command routing, music playback, web search, and basic system controls—all wrapped in a modern CustomTkinter GUI.  By requiring user registration and voice verification before executing commands, SafeTone puts a strong emphasis on privacy and authentication while still providing a convenient hands‑free experience.

## Why SafeTone?

Most consumer voice assistants sacrifice privacy by streaming your voice to cloud services or by allowing anyone in the room to trigger potentially sensitive actions.  SafeTone takes a different approach:

* **Controlled access** – every user must register and provide a voice sample before the assistant will respond to commands.  A super‑admin account can override voice matching if required.
* **Local processing** – enrolment and verification of voiceprints happens locally using [SpeechBrain](https://speechbrain.github.io/).  No biometric data is sent to external services.
* **Transparent architecture** – the assistant is written in pure Python using open‑source libraries.  Recruiters and security auditors can inspect the code to understand how authentication and command handling is implemented.

## Features

* **User registration & login** – secure sign‑up with email and password stored in a SQLite database.  After registering, users must record a short voice profile.
* **Speaker verification** – uses SpeechBrain’s pretrained `speaker-verification-wav2vec2` model to verify that the speaker matches the enrolled voice.  Commands from unauthenticated voices are rejected.
* **CustomTkinter interface** – modern dark‑mode GUI with registration, login and assistant control panels.
* **Natural‑language commands** – say things like “play music,” “what time is it,” “tell me a joke,” “open YouTube,” or “volume up.”  The assistant maps phrases to actions using a fuzzy command router.
* **Music player** – scans a configurable music folder (`D:\Music` by default) and plays MP3, WAV or OGG files.  Supports play, pause, resume, next, previous, shuffle and stop.
* **Web search and site opening** – integrates with `speech_recognition` and Google’s speech API to transcribe commands, then opens websites or searches Google in your default browser.
* **System controls** – restart or shut down the PC, put it to sleep, and adjust system volume using built‑in Windows commands (requires running on Windows).
* **Logging** – writes assistant actions and errors to `assistant.log` for debugging and audit purposes.
* **Extensible architecture** – the code is organized into modules (`database_manager.py`, `voice_key.py`, `routing.py`, `music.py`, etc.) to make adding new commands or services straightforward.

## Requirements

* **Operating system** – Windows 10 or later.  Some system commands and volume controls rely on Windows APIs and may not work on Linux or macOS.
* **Python** – version 3.10 or 3.11 is recommended.  Other versions may work but are not tested.
* **Audio hardware** – a microphone for recording commands and a speaker/headphones for playback.
* **Internet connection** – required for speech‑to‑text via Google’s free API and for opening websites.  Voice verification runs locally.

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/safetone.git
   cd safetone
   ```

2. **Create a virtual environment (optional but recommended)**

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # on Windows
   # or on PowerShell
   # .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   Install the required Python packages using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

   The `requirements.txt` file specifies versions for `CustomTkinter`, `SpeechRecognition`, `SpeechBrain`, `torch`, `torchaudio`, `pygame`, `pyttsx3`, `bcrypt`, and other necessary libraries.  You may need to install the Microsoft Visual C++ Build Tools and ensure that your Python installation can compile PyTorch and torchaudio.

4. **Configure the music folder (optional)**

   By default, SafeTone looks for audio files in `D:\Music`.  To change this, you can either:

   * Set the environment variable `VOICE_ASSISTANT_MUSIC_FOLDER` to your music directory, **or**
   * Edit the `music_folder` default in `config.py`.

   Only files with extensions listed in `Config.music_extensions` (MP3, WAV, OGG) will be added to the playlist.

5. **Run the application**

   ```bash
   python main_app.py
   ```

   On first launch you will be prompted to register.  Enter your name, email, password and phone number, then record your voice profile.  After registration, log in with your credentials and start issuing commands.

6. **Build a standalone executable (optional)**

   SafeTone can be packaged for distribution using [PyInstaller](https://pyinstaller.org/).  A `VoiceAssistant.spec` file is included.  To build a Windows executable:

   ```bash
   pip install pyinstaller
   pyinstaller VoiceAssistant.spec
   ```

   The bundled application will appear under the `dist/` directory.  Make sure to include the `pretrained_models` folder and any voiceprints when distributing.

## Usage

After logging in and verifying your voice, speak commands naturally.  Some examples:

| Command                               | Action                                                     |
|---------------------------------------|------------------------------------------------------------|
| “Play music”                          | Start playing music from your library                     |
| “Pause” / “Resume”                    | Control playback                                           |
| “Next song” / “Previous song”         | Skip forward or backward                                   |
| “Shuffle”                             | Randomize the playlist                                     |
| “Stop music”                          | Stop playback completely                                   |
| “What time is it?”                    | Tell the current time                                      |
| “Tell me a joke”                      | Hear a random joke                                         |
| “Open YouTube”                        | Launch YouTube in your default browser                     |
| “Search how to make pancakes”         | Perform a Google search                                    |
| “Volume up” / “Volume down”           | Adjust system volume                                       |
| “Shutdown” / “Restart” / “Sleep”      | Control your PC (requires confirmation for critical actions)|

If the assistant responds with “I did not understand that,” try rephrasing your command or speak clearly into the microphone.

## Project Structure

```
├── config.py           # Configuration class with paths and tuning parameters
├── database_manager.py # SQLite helper functions for user registration & login
├── voice_key.py        # Voice enrollment and speaker verification using SpeechBrain
├── main_app.py         # CustomTkinter GUI, user authentication and assistant loop
├── routing.py          # Maps natural‑language phrases to actions
├── music.py            # Music player wrapper using pygame
├── search.py           # Web search and site opening functions
├── system_controls.py  # Windows system operations: shutdown, restart, sleep, volume
├── tts.py              # Text‑to‑speech via pyttsx3
├── utilities.py        # Shared helper functions
├── jokes_time.py       # Tell a joke and tell the time
├── requirements.txt    # Python dependency versions
├── users.db            # SQLite database storing registered users (excluded from Git)
├── voiceprints/        # Enrolled voice profiles (excluded from Git)
├── pretrained_models/  # SpeechBrain pretrained models (excluded from Git)
└── assistant.log       # Runtime logs (rotated)
```

The `sem6_project_1.pdf` file is an optional project report included for academic context.  It is not required to run the assistant.

## Precautions & Best Practices

* **Voice data** – voiceprints are stored locally in the `voiceprints/` folder.  Keep this directory secure; do not commit it to version control.  The `.gitignore` file ensures that voiceprints and the user database are not pushed to GitHub.
* **Environment** – run the assistant on Windows.  Volume and power controls are implemented via Windows APIs and will not work on other platforms.
* **Internet access** – the assistant uses Google’s free speech‑to‑text service.  Ensure you have a stable internet connection.  Voice verification does not require internet.
* **Compatibility** – `torch` and `torchaudio` may require specific versions of CUDA or CPU libraries.  Follow the [official installation guide](https://pytorch.org/get-started/locally/) if you encounter issues.
* **Safe usage** – shutting down or restarting your PC via voice commands should be done cautiously.  The application does not prompt for confirmation; if you say “shutdown,” Windows will immediately shut down.

## Contributing

Contributions are welcome!  If you’d like to add new commands or improve the GUI, please open an issue or submit a pull request.  When contributing, follow standard Python best practices: write clear docstrings, format your code with [black](https://github.com/psf/black), and include unit tests where possible.

## License

This project is provided under the MIT License.  See the `LICENSE` file for details.

## Acknowledgments

SafeTone relies on excellent open‑source projects including CustomTkinter, SpeechRecognition, SpeechBrain, PyTorch, torchaudio, pygame, pyttsx3 and bcrypt.  Thanks to the maintainers of these libraries for making this assistant possible.