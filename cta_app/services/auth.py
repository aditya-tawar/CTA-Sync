"""User persistence and credential verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

USERS_FILE = Path(__file__).resolve().parent.parent / "users.json"
DEFAULT_USERS = {
    "test_user": {
        "password": hashlib.sha256("test123".encode()).hexdigest(),
        "role": "user",
    }
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def initialize_users() -> None:
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps(DEFAULT_USERS, indent=4))


def load_users() -> dict:
    initialize_users()
    return json.loads(USERS_FILE.read_text())


def save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=4))


def save_user(username: str, password: str, role: str = "user") -> None:
    users = load_users()
    users[username] = {"password": hash_password(password), "role": role}
    save_users(users)


def verify_credentials(username: str, password: str) -> tuple[bool, str | None]:
    try:
        user_data = load_users().get(username)
        if user_data is None:
            return False, None

        if isinstance(user_data, dict):
            stored_hash = user_data.get("password")
            role = user_data.get("role", "user")
        else:
            stored_hash = user_data
            role = "user"

        if hash_password(password) == stored_hash:
            return True, role
    except Exception as error:
        print(f"Auth error: {error}")

    return False, None

