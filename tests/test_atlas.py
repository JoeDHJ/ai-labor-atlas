import csv
import tempfile
import unittest
from pathlib import Path

from ai_labor_atlas.demo import FIELDS, demo_rows
from ai_labor_atlas.metrics import group_by_major_soc, summarize
from ai_labor_atlas.pipeline import build_dataset


class AtlasTests(unittest.TestCase):
    def test_demo_has_contract_and_summary(self):
        rows = demo_rows()
        self.assertEqual(len(rows), 8)
        self.assertEqual(set(rows[0]), set(FIELDS))
        result = summarize(
            [{key: str(value) for key, value in row.items()} for row in rows]
        )
        self.assertEqual(result["rows"], 8)
        self.assertGreater(result["exposure_coverage"], 0.99)

    def test_demo_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            processed = Path(temp) / "processed"
            manifest = build_dataset(Path(temp) / "raw", processed, demo=True)
            self.assertEqual(manifest["row_count"], 8)
            with (processed / "occupations.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 8)

    def test_grouping(self):
        rows = [{key: str(value) for key, value in row.items()} for row in demo_rows()]
        groups = group_by_major_soc(rows)
        self.assertTrue(any(group["soc_major"] == "15" for group in groups))


if __name__ == "__main__":
    unittest.main()
