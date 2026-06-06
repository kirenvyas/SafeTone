"""
Run: python diagnose.py
Checks the local environment for the key dependencies required by this project.
"""

from __future__ import annotations

import importlib
import platform
import sys

PACKAGES = [
    "customtkinter",
    "numpy",
    "speech_recognition",
    "sounddevice",
    "soundfile",
    "torch",
    "torchaudio",
    "speechbrain",
    "bcrypt",
    "pygame",
    "pyttsx3",
]

print("Python:", sys.version)
print("Platform:", platform.platform())
print()

for pkg in PACKAGES:
    try:
        mod = importlib.import_module(pkg)
        version = getattr(mod, "__version__", "unknown")
        print(f"[ OK ] {pkg:<18} version={version}")
    except Exception as exc:
        print(f"[FAIL] {pkg:<18} {exc}")

print("""
Recommended clean install for the voice stack:
  pip uninstall torch torchaudio speechbrain huggingface_hub numpy -y
  pip install numpy==1.26.4
  pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
  pip install speechbrain==0.5.16 huggingface_hub==0.19.4
""")
