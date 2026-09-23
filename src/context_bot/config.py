from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_username: str
    data_dir: Path

    @property
    def users_file(self) -> Path:
        return self.data_dir / "users.json"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN environment variable is required")

        return cls(
            bot_token=token,
            admin_username=os.getenv("BOT_ADMIN_USERNAME", "ssllvvtt").lstrip("@"),
            data_dir=Path(os.getenv("CONTEXT_BOT_DATA_DIR", "data")),
        )
