import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from context_bot.storage import UserRepository


class UserRepositoryTest(unittest.TestCase):
    def test_adds_each_user_once(self) -> None:
        with TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "users.json")

            self.assertTrue(repository.add(42, "alice"))
            self.assertFalse(repository.add(42, "renamed"))
            self.assertEqual(repository.all(), [{"id": 42, "username": "alice"}])

    def test_treats_empty_file_as_empty_storage(self) -> None:
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "users.json"
            file_path.write_text("", encoding="utf-8")

            repository = UserRepository(file_path)

            self.assertEqual(repository.all(), [])

    def test_does_not_silently_overwrite_invalid_json(self) -> None:
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "users.json"
            file_path.write_text("not-json", encoding="utf-8")
            repository = UserRepository(file_path)

            with self.assertRaises(json.JSONDecodeError):
                repository.add(42, "alice")

            self.assertEqual(file_path.read_text(encoding="utf-8"), "not-json")


if __name__ == "__main__":
    unittest.main()
