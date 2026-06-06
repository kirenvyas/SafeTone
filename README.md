# SafeTone: Secure Command-Based Windows Voice Assistant

SafeTone is a secure, command-based desktop voice assistant for Windows built with Python. It combines user authentication, mandatory voice enrollment, speaker verification, command routing, music playback, web search, text-to-speech feedback, and Windows system controls inside a modern CustomTkinter-based interface.

The project is designed to demonstrate practical application development, local biometric verification, modular Python architecture, and security-conscious handling of user data.

---

## Table of Contents

- [Why SafeTone?](#why-safetone)
- [Demo / Screenshots](#demo--screenshots)
- [Key Features](#key-features)
- [Security & Access Model](#security--access-model)
- [Tech Stack](#tech-stack)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Verify Installation](#verify-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Precautions & Best Practices](#precautions--best-practices)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Build Executable](#build-executable)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Why SafeTone?

Most basic voice assistants execute commands without verifying who is speaking. SafeTone adds a security layer by requiring users to register, enroll their voice, and authenticate before commands are executed.

SafeTone focuses on:

- **Secure access** through login and voice enrollment.
- **Speaker verification** before executing voice commands.
- **Local storage of user and voice data** instead of exposing biometric files publicly.
- **Modular architecture** so each feature can be reviewed, tested, and improved independently.
- **Windows-first command execution** for practical desktop assistant use cases.

---

## Demo / Screenshots

The following screenshots are recommended for a complete GitHub presentation:

- Login screen
- User registration screen
- Voice enrollment flow
- Main assistant dashboard
- Music player / command panel
- Successful voice authentication message

Suggested folder structure for future screenshots:

```text
docs/
└── screenshots/
    ├── login-screen.png
    ├── registration-screen.png
    ├── voice-enrollment.png
    ├── assistant-dashboard.png
    └── music-player-panel.png
```

After adding screenshots, you can embed them like this:

```markdown
![Login Screen](docs/screenshots/login-screen.png)
![Assistant Dashboard](docs/screenshots/assistant-dashboard.png)
```

---

## Key Features

- **User registration and login**
  - Register users with name, email, password, and phone number.
  - Store user records locally using SQLite.
  - Support password-based authentication.

- **Mandatory voice enrollment**
  - New users must record their voice before using assistant commands.
  - Voice profiles are stored locally and should never be committed to GitHub.

- **Speaker verification**
  - Uses SpeechBrain speaker verification to compare the live speaker with enrolled voiceprints.
  - Helps prevent unauthorized command execution.

- **Admin override support**
  - The first registered user automatically becomes the admin.
  - Users registered after the first account are treated as normal users.
  - The admin can authenticate using the admin voice profile and override voice verification to run commands inside any logged-in user account.
  - This is useful for system recovery, testing, and controlled administrative access.

- **Modern GUI**
  - Built with CustomTkinter.
  - Provides a cleaner Windows desktop application experience than a basic terminal interface.

- **Voice command routing**
  - Routes recognized commands to the correct module.
  - Supports natural commands for music, web search, time, jokes, and system controls.

- **Music playback**
  - Plays audio files from a configurable local music folder.
  - Supports play, pause, resume, stop, next, previous, and shuffle.

- **Web and browser commands**
  - Opens websites such as YouTube or Google.
  - Performs Google searches from voice input.

- **Text-to-speech feedback**
  - Uses pyttsx3 to provide spoken responses.

- **Windows system controls**
  - Supports selected Windows actions such as shutdown, restart, sleep, and volume control depending on system permissions.

- **Logging**
  - Stores runtime logs locally for debugging and traceability.

---

## Security & Access Model

SafeTone uses a layered local authentication flow:

```text
User launches app
        ↓
Login / register
        ↓
Voice enrollment required
        ↓
Live voice command captured
        ↓
Speaker verification
        ↓
Command executed only after authorization
```

### Admin behavior

- The **first registered user becomes the admin automatically**.
- All later registrations are normal user accounts.
- The admin voice profile can be used for override authentication.
- Admin override allows the admin to authorize and run commands even when another user account is logged in.
- Protect the admin password and admin voiceprint carefully.

### Sensitive data

The following files and folders must remain local and must not be pushed to GitHub:

```text
users.db
voiceprints/
pretrained_models/
assistant.log
temp_command.wav
```

These are excluded in `.gitignore` for privacy and repository hygiene.

---

## Tech Stack

| Area | Technology |
|---|---|
| Programming language | Python |
| GUI | CustomTkinter |
| Database | SQLite |
| Password handling | bcrypt |
| Speech recognition | SpeechRecognition |
| Speaker verification | SpeechBrain |
| ML backend | PyTorch, torchaudio |
| Audio playback | pygame |
| Text-to-speech | pyttsx3 |
| System control | Windows OS commands / APIs |
| Packaging | PyInstaller |

For the complete dependency list and exact versions, see [`requirements.txt`](requirements.txt).

Key dependencies include:

- CustomTkinter
- SpeechRecognition
- SpeechBrain
- torch
- torchaudio
- pygame
- pyttsx3
- bcrypt
- PyInstaller

---

## System Requirements

### Required

- Windows 10 or Windows 11
- Python 3.10 or Python 3.11
- Working microphone
- Speaker or headphones
- Internet connection for speech-to-text recognition
- Local disk space for model files and runtime data

> **Important Python note:** Python 3.12+ may have compatibility issues with some audio, ML, or speaker-verification dependencies. Python 3.10 or 3.11 is recommended for the best compatibility.

### Recommended system specs

- RAM: 4 GB minimum, 8 GB or higher recommended
- Disk space: 2 GB or higher recommended, especially when pretrained models are downloaded locally
- Microphone: USB or built-in microphone
- Audio quality: quiet room recommended for enrollment and verification
- Internet: stable connection for Google Speech Recognition through the SpeechRecognition package

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/kirenvyas/SafeTone.git
cd SafeTone
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows Command Prompt:

```cmd
.venv\Scripts\activate
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python main_app.py
```

---

## Verify Installation

After running:

```bash
python main_app.py
```

Confirm the following:

- [ ] Login screen appears
- [ ] New user registration works
- [ ] First registered user is treated as admin
- [ ] Voice enrollment screen opens after registration
- [ ] Microphone recording works
- [ ] Text-to-speech output is audible
- [ ] Voice verification completes successfully
- [ ] Basic command execution works
- [ ] Music command works after setting the correct music folder path

---

## Configuration

### Music folder path

By default, SafeTone may use a local folder such as:

```text
D:\Music
```

Before running music commands, make sure this path exists on your system.

You can update the music folder in one of the following ways:

### Option 1: Environment variable

Set a Windows environment variable:

```powershell
setx VOICE_ASSISTANT_MUSIC_FOLDER "D:\Music"
```

Restart the terminal after setting the variable.

### Option 2: Update `config.py`

Open `config.py` and update the music folder path according to your local system.

Example:

```python
music_folder = r"D:\Music"
```

Supported audio file formats usually include:

```text
.mp3
.wav
.ogg
```

---

## Usage

After login and voice verification, speak commands naturally.

| Example Command | Expected Action |
|---|---|
| "Play music" | Starts music playback |
| "Pause music" | Pauses current track |
| "Resume music" | Resumes playback |
| "Next song" | Plays next song |
| "Previous song" | Plays previous song |
| "Shuffle music" | Shuffles playlist |
| "Stop music" | Stops music playback |
| "What time is it?" | Speaks current time |
| "Tell me a joke" | Speaks a joke |
| "Open YouTube" | Opens YouTube in browser |
| "Search Python tutorials" | Searches Google |
| "Volume up" | Increases system volume |
| "Volume down" | Decreases system volume |
| "Shutdown" | Executes configured shutdown command |
| "Restart" | Executes configured restart command |
| "Sleep" | Executes configured sleep command |

> Use system-level commands carefully. Shutdown, restart, and sleep commands can affect the active Windows session.

---

## Project Structure

```text
SafeTone/
├── README.md               # Project documentation
├── LICENSE                 # Project license
├── .gitignore              # Git ignore rules for Python, local data, and security
├── requirements.txt        # Python dependencies
├── VoiceAssistant.spec     # PyInstaller build configuration
├── main_app.py             # Main GUI application and assistant flow
├── config.py               # Project configuration and local paths
├── database_manager.py     # SQLite user database operations
├── voice_key.py            # Voice enrollment and speaker verification
├── listener.py             # Microphone listening and command capture
├── routing.py              # Voice command routing logic
├── music.py                # Music playback logic
├── search.py               # Web search / browser command logic
├── system_controls.py      # Windows system control actions
├── tts.py                  # Text-to-speech response handling
├── jokes_time.py           # Joke and time utilities
├── utilities.py            # Shared helper functions
├── logger.py               # Logging helper
├── logging_config.py       # Logging configuration
└── reset_data.py           # Local reset utility for development/testing
```

Runtime files and private data are intentionally excluded from GitHub:

```text
users.db
voiceprints/
pretrained_models/
assistant.log
temp_command.wav
```

---

## Precautions & Best Practices

### Privacy

- Do not commit user databases, voiceprints, recordings, or logs.
- Treat voiceprints as biometric data.
- Keep the admin account and admin voice profile secure.

### Internet connectivity

- Speech-to-text recognition requires internet access when using Google Speech Recognition through the SpeechRecognition package.
- Speaker verification is designed to run locally after the required model files are available.

### Windows dependency

- This project is designed for Windows.
- Some system commands and volume controls may not work on Linux or macOS.

### Voice enrollment quality

For best speaker verification results:

- Record in a quiet room.
- Use the same microphone for enrollment and daily use when possible.
- Speak clearly and naturally.
- Avoid background music or fan noise.

### Model files

- Pretrained models can be large.
- Keep model folders local.
- Do not commit model files to GitHub.
- Document setup steps instead of uploading large models.

---

## Troubleshooting

### Voice recognition not working

- Check that your microphone is connected.
- Confirm the microphone is enabled in Windows Sound settings.
- Make sure the correct input device is selected.
- Check your internet connection.
- Speak clearly and closer to the microphone.
- Restart the application after changing audio devices.

### Speaker verification failing

- Re-enroll the voice profile.
- Use a quiet environment during enrollment.
- Avoid using different microphones between enrollment and verification.
- Delete the local voiceprint only when you intentionally want to re-register or reset a user.

### Text-to-speech not audible

- Check Windows speaker volume.
- Confirm output device is selected correctly.
- Test pyttsx3 separately if needed.
- Restart the app after switching audio output devices.

### Music not playing

- Confirm the music folder path exists.
- Confirm the folder contains supported audio files.
- Check file extensions such as `.mp3`, `.wav`, or `.ogg`.
- Update the music folder path in `config.py` or through the environment variable.

### Torch / torchaudio installation issues

- Use Python 3.10 or 3.11.
- Upgrade pip before installing requirements.
- Install Microsoft Visual C++ Build Tools if required.
- Follow the official PyTorch installation command suitable for your system if torch installation fails.

### App window does not open

- Confirm all dependencies are installed.
- Run the app from an activated virtual environment.
- Check terminal error logs.
- Review `assistant.log` if it exists locally.

---

## Development

### Recommended development setup

```bash
git clone https://github.com/kirenvyas/SafeTone.git
cd SafeTone
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Manual smoke testing

Before committing changes, verify:

- [ ] App starts without errors
- [ ] Registration works
- [ ] Login works
- [ ] Voice enrollment works
- [ ] Voice verification works
- [ ] Basic commands work
- [ ] Music commands work with a valid music folder
- [ ] No private runtime files are staged in Git

### Optional automated tests

If a `tests/` folder is added in future, tests can be run with:

```bash
pytest tests/
```

---

## Build Executable

SafeTone can be packaged as a Windows executable using PyInstaller.

```bash
pip install pyinstaller
pyinstaller VoiceAssistant.spec
```

Build output is generated inside:

```text
dist/
```

Important build notes:

- Do not commit `dist/` or `build/` folders.
- Keep `VoiceAssistant.spec` committed because it documents the reproducible build configuration.
- Do not include private `users.db` or `voiceprints/` in public builds.
- For private offline distribution, include model files only when licensing and size requirements are acceptable.

---

## Roadmap

Planned or recommended future improvements:

- Add confirmation prompts for shutdown/restart commands
- Add screenshots and demo GIFs
- Add automated tests
- Add role management screen for admin/user control
- Add safer command permissions per user
- Add offline speech-to-text option
- Add encrypted local voiceprint storage
- Add GitHub Actions workflow for linting
- Add packaging guide for Windows installer

---

## Contributing

Contributions are welcome.

Recommended contribution flow:

1. Fork the repository
2. Create a new feature branch
3. Make changes with clear commit messages
4. Test the application locally
5. Open a pull request with a clear description

Please do not submit private data, voiceprints, logs, database files, model downloads, or generated executables.

---

## License

This project is licensed under the MIT License.

See the [`LICENSE`](LICENSE) file for details.

---

## Acknowledgments

SafeTone uses and appreciates the following open-source technologies:

- CustomTkinter
- SpeechRecognition
- SpeechBrain
- PyTorch
- torchaudio
- pygame
- pyttsx3
- bcrypt
- PyInstaller

---

## Author

**Kiren Vyas**  
GitHub: [kirenvyas](https://github.com/kirenvyas)

Repository: [SafeTone](https://github.com/kirenvyas/SafeTone)
