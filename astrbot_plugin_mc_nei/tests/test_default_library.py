import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DefaultLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = json.loads((ROOT / "data" / "default_command_library.json").read_text(encoding="utf-8"))

    def test_library_metadata_and_shape(self):
        self.assertEqual(self.library.get("name"), "默认命令库")
        self.assertEqual(self.library.get("author"), "CA制作组")
        self.assertIsInstance(self.library.get("idlist"), list)
        self.assertIsInstance(self.library.get("enums"), dict)

    def test_command_field_is_empty_in_uploaded_source(self):
        self.assertEqual(self.library.get("commands"), {})

    def test_library_contains_full_enum_tables(self):
        count = sum(len(group) for group in self.library["enums"].values() if isinstance(group, dict))
        self.assertGreaterEqual(count, 9000)
        self.assertIn("diamond", self.library["enums"]["item"])
        self.assertIn("command_block", self.library["enums"]["block"])
        self.assertIn("zombie", self.library["enums"]["entity"])
        self.assertIn("ambient.cave", self.library["enums"]["sound"])


if __name__ == "__main__":
    unittest.main()
