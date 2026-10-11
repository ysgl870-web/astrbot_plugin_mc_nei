import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginDataTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))

    def test_commands_are_well_formed(self):
        rows = self.load("commands.json")
        self.assertGreaterEqual(len(rows), 25)
        self.assertTrue(all(row.get("name") and row.get("syntax") for row in rows))

    def test_ids_are_well_formed(self):
        rows = self.load("ids.json")
        self.assertGreaterEqual(len(rows), 50)
        self.assertTrue(all(row.get("name") and row.get("id", "").startswith("minecraft:") for row in rows))
        self.assertTrue(all(row.get("type") in {"物品", "方块", "实体"} for row in rows))

    def test_expected_records_exist(self):
        commands = self.load("commands.json")
        ids = self.load("ids.json")
        self.assertTrue(any(x["name"] == "give" for x in commands))
        self.assertTrue(any(x["id"] == "minecraft:diamond" for x in ids))
        self.assertTrue(any(x["id"] == "minecraft:zombie" for x in ids))


if __name__ == "__main__":
    unittest.main()
