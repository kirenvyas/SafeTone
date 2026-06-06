from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional
from config import CFG
from contextlib import closing

log = logging.getLogger(__name__)

_DB_PATH = CFG.db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    contact       TEXT    NOT NULL UNIQUE,
    voice_path    TEXT    NOT NULL DEFAULT '',
    role          TEXT    NOT NULL DEFAULT 'User'
                          CHECK(role IN ('Super Admin', 'User'))
);
"""


def set_database_path(path: str | Path) -> None:
    global _DB_PATH
    _DB_PATH = Path(path)


# password helpers -----------------------------------------------------------

def _bcrypt_module():
    try:
        import bcrypt  # type: ignore
        return bcrypt
    except Exception:
        return None


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")
    bcrypt = _bcrypt_module()
    if bcrypt is not None:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False

    if stored_hash.startswith("$2"):
        bcrypt = _bcrypt_module()
        if bcrypt is None:
            log.warning("bcrypt hash stored but bcrypt module unavailable.")
            return False
        try:
            return bool(bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")))
        except Exception:
            log.exception("bcrypt password verification failed.")
            return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, salt_hex, digest_hex = stored_hash.split("$", 2)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
            )
            return hmac.compare_digest(actual, expected)
        except Exception:
            log.exception("PBKDF2 password verification failed.")
            return False

    return False


# sqlite helpers -------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _is_empty() -> bool:
    with closing(_connect()) as conn:
        with conn:
            return conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0] == 0


def initialize_database() -> None:
    with closing(_connect()) as conn:
        with conn:
            conn.executescript(_SCHEMA)
    log.info("Database initialised at '%s'.", _DB_PATH)


def register_user(name: str, email: str, password: str, contact: str, voice_path: str) -> dict:
    name = name.strip()
    email = email.strip().lower()
    contact = contact.strip()

    if not all([name, email, password, contact]):
        return {"success": False, "message": "All fields are required."}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    password_hash = hash_password(password)
    role = "Super Admin" if _is_empty() else "User"

    try:
        with closing(_connect()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash, contact, voice_path, role) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, email, password_hash, contact, voice_path, role),
                )
        return {
            "success": True,
            "message": f"Registration successful! You are registered as {role}.",
        }
    except sqlite3.IntegrityError as exc:
        detail = str(exc).lower()
        if "email" in detail:
            message = "That email address is already registered."
        elif "contact" in detail:
            message = "That contact number is already registered."
        else:
            message = "A user with these details already exists."
        log.warning("Registration integrity error: %s", exc)
        return {"success": False, "message": message}
    except sqlite3.Error:
        log.exception("Unexpected database error during registration.")
        return {"success": False, "message": "A database error occurred. Please try again."}


def login_user(name: str, contact: str, password: str) -> dict:
    name = name.strip()
    contact = contact.strip()

    if not all([name, contact, password]):
        return {"success": False, "message": "Name, contact, and password are required.", "user": None}

    try:
        with closing(_connect()) as conn:
            with conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE name = ? COLLATE NOCASE AND contact = ?",
                    (name, contact),
                ).fetchone()
        if row is None:
            return {
                "success": False,
                "message": "No account found with that name and contact number.",
                "user": None,
            }
        user = _row_to_dict(row)
        if not verify_password(password, user["password_hash"]):
            return {"success": False, "message": "Incorrect password.", "user": None}
        return {"success": True, "message": "Login successful.", "user": user}
    except sqlite3.Error:
        log.exception("Database error during login.")
        return {
            "success": False,
            "message": "A database error occurred. Please try again.",
            "user": None,
        }


def get_user_by_name_contact(name: str, contact: str) -> Optional[dict]:
    try:
        with closing(_connect()) as conn:
            with conn:
                row = conn.execute(
                    "SELECT * FROM users WHERE name = ? COLLATE NOCASE AND contact = ?",
                    (name.strip(), contact.strip()),
                ).fetchone()
        return _row_to_dict(row) if row else None
    except sqlite3.Error:
        log.exception("Failed to fetch user by name/contact.")
        return None


def get_super_admin() -> Optional[dict]:
    try:
        with closing(_connect()) as conn:
            with conn:
                row = conn.execute("SELECT * FROM users WHERE role = 'Super Admin' LIMIT 1").fetchone()
        return _row_to_dict(row) if row else None
    except sqlite3.Error:
        log.exception("Failed to fetch Super Admin.")
        return None


def get_all_voice_paths() -> list[tuple[int, str, str]]:
    try:
        with closing(_connect()) as conn:
            with conn:
                rows = conn.execute(
                    "SELECT id, name, voice_path FROM users WHERE voice_path IS NOT NULL AND voice_path != ''"
                ).fetchall()
        return [(r["id"], r["name"], r["voice_path"]) for r in rows]
    except sqlite3.Error:
        log.exception("Failed to fetch voice paths.")
        return []

def close_connection(conn):
    try:
        if conn:
            conn.close()
    except Exception:
        pass

def reset_all_data() -> None:
    if _DB_PATH.exists():
        _DB_PATH.unlink()
