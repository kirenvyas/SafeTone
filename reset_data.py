from __future__ import annotations

import shutil
from pathlib import Path

from config import CFG

BASE = Path(__file__).resolve().parent

deleted = []
for path in (CFG.db_path, BASE / "temp_command.wav"):
    if path.exists():
        path.unlink()
        deleted.append(str(path))

voiceprints = CFG.voiceprints_dir
if voiceprints.exists():
    shutil.rmtree(voiceprints)
    deleted.append(str(voiceprints))

if deleted:
    print("Deleted:")
    for item in deleted:
        print(f"  {item}")
else:
    print("Nothing to delete — already clean.")
