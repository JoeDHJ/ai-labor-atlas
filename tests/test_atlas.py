import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from ai_labor_atlas.dashboard import render
from ai_labor_atlas.demo import TASK_FIELDS, FIELDS, demo_rows, demo_tasks
from ai_labor_atlas.distance import OccupationBridge
from ai_labor_atlas.metrics import group_by_major_soc, summarize, summarize_tasks
from ai_labor_atlas.pipeline import (
    _load_oews,
    _load_projections,
    _load_tasks,
    build_dataset,
)

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

        tasks = demo_tasks()
        self.assertEqual(set(tasks[0]), set(TASK_FIELDS))
        task_summary = summarize_tasks(
            [{key: str(value) for key, value in row.items()} for row in rows],
            [{key: str(value) for key, value in row.items()} for row in tasks],
        )
        self.assertEqual(task_summary["task_rows"], 16)
        self.assertEqual(task_summary["task_occupation_coverage"], 1.0)

    def test_demo_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            processed = Path(temp) / "processed"
            manifest = build_dataset(Path(temp) / "raw", processed, demo=True)
            self.assertEqual(manifest["row_count"], 8)
            self.assertEqual(manifest["task_row_count"], 16)
            with (processed / "occupations.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 8)
            with (processed / "tasks.csv").open(newline="", encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 16)

    def test_task_statements_are_loaded_with_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Task Statements.txt").write_text(
                "\t".join(
                    [
                        "O*NET-SOC Code",
                        "Task ID",
                        "Task",
                        "Task Type",
                        "Incumbents Responding",
                        "Date",
                        "Domain Source",
                    ]
                )
                + "\n"
                + "\t".join(
                    [
                        "15-1252.00",
                        "8823",
                        "Build software systems.",
                        "Core",
                        "95",
                        "08/2023",
                        "Incumbent",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            tasks = _load_tasks(root)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0]["task_id"], "8823")
            self.assertEqual(tasks[0]["source_file"], "Task Statements.txt")

    def test_dashboard_includes_task_filter_and_task_payload(self):
        rows = [{key: str(value) for key, value in row.items()} for row in demo_rows()]
        tasks = [
            {key: str(value) for key, value in row.items()} for row in demo_tasks()
        ]
        page = render(rows, summarize(rows), [], tasks)
        self.assertIn('id="task-filter"', page)
        self.assertIn('id="task-type-filter"', page)
        self.assertIn("Core tasks", page)
        self.assertIn("tasks_by_onet", page)
        self.assertIn("Design, develop, and test software applications.", page)
        self.assertIn('id="bridge-select"', page)
        self.assertIn("Career bridge", page)

    def test_occupation_bridge_keeps_distance_evidence_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp)
            header = "O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\n"
            for filename, element, name in [
                ("Essential Skills.txt", "2.A.1.a", "Reading Comprehension"),
                ("Transferable Skills.txt", "2.B.1.a", "Social Perceptiveness"),
                ("Knowledge.txt", "2.C.1.a", "Administration and Management"),
                ("Abilities.txt", "1.A.1.a", "Oral Comprehension"),
                ("Work Activities.txt", "4.A.1.a.1", "Getting Information"),
            ]:
                (raw / filename).write_text(
                    header
                    + f"15-1252.00\t{element}\t{name}\tIM\t4.0\n"
                    + f"13-2011.00\t{element}\t{name}\tIM\t3.0\n",
                    encoding="utf-8",
                )
            (raw / "Software Skills.txt").write_text(
                "O*NET-SOC Code\tWorkplace Example\tElement ID\tElement Name\tHot Technology\tIn Demand\n"
                "15-1252.00\tPython\t2.E.1.a\tProgramming\tY\tY\n"
                "13-2011.00\tMicrosoft Excel\t2.E.1.a\tSpreadsheet\tY\tY\n",
                encoding="utf-8",
            )
            rows = [
                {key: str(value) for key, value in row.items()}
                for row in demo_rows()[:2]
            ]
            bridge = OccupationBridge(raw, rows, demo_tasks()[:4])
            result = bridge.bridge(rows[0]["onet_soc_code"])
            self.assertTrue(result["available"])
            self.assertEqual(result["source"]["profile_source"], "exact")
            self.assertTrue(result["candidates"])
            candidate = result["candidates"][0]
            self.assertIn("structured_distance", candidate)
            self.assertIn("software_overlap", candidate)
            self.assertIn("shared_task_evidence", candidate)

    def test_occupation_bridge_is_explicit_when_structured_data_is_missing(self):
        rows = [{key: str(value) for key, value in row.items()} for row in demo_rows()]
        bridge = OccupationBridge(Path("Z:\\missing-onet"), rows, demo_tasks())
        result = bridge.bridge(rows[0]["onet_soc_code"])
        self.assertFalse(result["available"])
        self.assertEqual(result["error"], "structured_onet_profiles_unavailable")

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
