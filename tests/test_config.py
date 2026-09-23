import os
from pathlib import Path
import unittest
from unittest.mock import patch

from context_bot.config import Settings


class SettingsTest(unittest.TestCase):
    def test_reads_environment(self) -> None:
        environment = {
            "BOT_TOKEN": "test-token",
            "BOT_ADMIN_USERNAME": "@admin",
            "CONTEXT_BOT_DATA_DIR": "runtime",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.bot_token, "test-token")
        self.assertEqual(settings.admin_username, "admin")
        self.assertEqual(settings.data_dir, Path("runtime"))

    def test_requires_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "BOT_TOKEN"):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
