import json
from pathlib import Path
from threading import Lock
from typing import TypedDict


class User(TypedDict):
    id: int
    username: str | None


class UserRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = Lock()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write([])

    def all(self) -> list[User]:
        with self._lock:
            return self._read()

    def add(self, user_id: int, username: str | None) -> bool:
        with self._lock:
            users = self._read()
            if any(user["id"] == user_id for user in users):
                return False

            users.append({"id": user_id, "username": username})
            self._write(users)
            return True

    def replace(self, users: list[User]) -> None:
        with self._lock:
            self._write(users)

    def _read(self) -> list[User]:
        content = self.file_path.read_text(encoding="utf-8").strip()
        return json.loads(content) if content else []

    def _write(self, users: list[User]) -> None:
        self.file_path.write_text(
            json.dumps(users, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
