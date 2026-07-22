import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from ai_labor_atlas.demo import FIELDS, demo_rows
from ai_labor_atlas.metrics import group_by_major_soc, summarize
from ai_labor_atlas.pipeline import _load_oews, _load_projections, build_dataset

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover - optional Excel dependency
    Workbook = None


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

    @unittest.skipUnless(Workbook, "openpyxl is required for Excel parser tests")
    def test_bls_excel_inputs_are_parsed_with_explicit_units(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            oews_zip = root / "bls_oews_may_2025.zip"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["OCC_CODE", "TOT_EMP", "A_MEDIAN"])
            sheet.append(["15-1252", 1000, 50000])
            content = io.BytesIO()
            workbook.save(content)
            with zipfile.ZipFile(oews_zip, "w") as archive:
                archive.writestr("national.xlsx", content.getvalue())

            projection_path = root / "bls_projections_2024_2034.xlsx"
            projection_book = Workbook()
            projection_book.remove(projection_book.active)
            projection_sheet = projection_book.create_sheet("Table 1.2")
            projection_sheet.append(["Table 1.2 title"])
            projection_sheet.append(
                [
                    "2024 National Employment Matrix title",
                    "2024 National Employment Matrix code",
                    "Employment, 2024",
                    "Employment, 2034",
                    "Employment change, percent, 2024-34",
                    "Occupational openings, 2024-34 annual average",
                ]
            )
            projection_sheet.append(
                ["Software Developers", "15-1252", 10.0, 12.0, 20.0, 1.2]
            )
            projection_book.save(projection_path)

            oews = _load_oews(root)
            projections = _load_projections(root)
            self.assertEqual(oews["15-1252"]["employment_2024"], 1000)
            self.assertEqual(projections["15-1252"]["annual_openings_2024_2034"], 1200)


if __name__ == "__main__":
    unittest.main()
