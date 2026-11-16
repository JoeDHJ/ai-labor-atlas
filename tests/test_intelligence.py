from __future__ import annotations

import io
import json
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ai_labor_atlas.cli import main
from ai_labor_atlas.demo import demo_rows
from ai_labor_atlas.intelligence import (
    build_research,
    exposure_case,
    load_market,
    market_comparison,
    parse_series,
    portfolio_snapshot,
    series_manifest,
    skill_composition,
    unique_soc,
    executive_brief,
)
from ai_labor_atlas.pipeline import _apply_relative_aioe_scale, build_dataset
from ai_labor_atlas.research_dashboard import write_research_site
from ai_labor_atlas.scenario import Scenario, run_scenario, sensitivity
from ai_labor_atlas.staffing import aggregate_staffing, parse_matrix, load_staffing
from ai_labor_atlas.metrics import aggregate_onet_rows
from ai_labor_atlas.io import write_csv
from ai_labor_atlas.sources import validate_projection_archive, download_file


class ScenarioTests(unittest.TestCase):
    def test_capacity_arithmetic_and_training_only_for_new_adopters(self):
        params = Scenario(
            workforce=100,
            years=2,
            annual_adoption=0.5,
            automation_task_share=0.2,
            augmentation_task_share=0.3,
            automation_saving=0.5,
            augmentation_saving=0.2,
            training_hours=20,
            training_effectiveness=0.5,
        )
        first, second = run_scenario(params)["trajectory"]
        self.assertEqual(first["adoption_share"], 0.5)
        self.assertEqual(second["adoption_share"], 0.75)
        self.assertEqual(first["automation_capacity_hours"], 10000)
        self.assertEqual(first["augmentation_capacity_hours"], 3000)
        self.assertEqual(first["training_hours"], 1000)
        self.assertEqual(second["training_hours"], 500)
        self.assertEqual(first["net_capacity_hours"], 12000)
        self.assertEqual(first["fte_equivalent_capacity"], 6)
        self.assertEqual(second["workforce_baseline"], 100)

    def test_zero_adoption_and_negative_net_capacity_are_preserved(self):
        self.assertEqual(
            run_scenario(Scenario(annual_adoption=0))["trajectory"][-1][
                "net_capacity_hours"
            ],
            0,
        )
        params = Scenario(automation_saving=0, augmentation_saving=0, annual_adoption=1)
        result = run_scenario(params)["trajectory"]
        self.assertLess(result[0]["net_capacity_hours"], 0)
        self.assertEqual(result[1]["training_hours"], 0)

    def test_rejects_invalid_and_ambiguous_parameters(self):
        for changes in (
            {"workforce": 0},
            {"years": 1.5},
            {"years": True},
            {"annual_adoption": math.nan},
            {"annual_adoption": math.inf},
            {"training_effectiveness": 1.1},
            {"training_hours": -1},
            {"training_hours": 2100},
            {"automation_task_share": 0.8, "augmentation_task_share": 0.5},
            {"workforce": "100"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                run_scenario(replace(Scenario(), **changes))
        with self.assertRaises(ValueError):
            run_scenario(Scenario(workforce=10**400))

    def test_sensitivity_changes_only_adoption(self):
        base = Scenario()
        cases = sensitivity(base)
        self.assertEqual([r["annual_adoption"] for r in cases], [0.125, 0.25, 0.375])
        self.assertEqual(
            cases[1]["net_capacity_hours"],
            run_scenario(base)["trajectory"][-1]["net_capacity_hours"],
        )

    def test_cli_runs_without_occupation_data_and_errors_cleanly(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"AI_LABOR_ATLAS_DATA_DIR": temp}),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["scenario", "--years", "2"]), 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "scenario")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["scenario", "--annual-adoption", "nan"]), 2)


class IntelligenceTests(unittest.TestCase):
    def test_archive_pin_validates_vintage_before_replacing_source(self):
        import zipfile
        from openpyxl import Workbook

        for year in (2024, 2025):
            workbook = Workbook()
            workbook.active.title = "Table 1.2"
            workbook.active.append(
                [
                    f"{year} National Employment Matrix code",
                    f"Employment, {year}",
                    f"Employment, {year + 10}",
                ]
            )
            buffer = io.BytesIO()
            workbook.save(buffer)
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("2024-34/occupation.xlsx", buffer.getvalue())
            payload = archive.getvalue()
            if year == 2024:
                validate_projection_archive(payload)
            else:
                with self.assertRaises(ValueError):
                    validate_projection_archive(payload)

                class Response:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                    def read(self):
                        return payload

                with (
                    tempfile.TemporaryDirectory() as temp,
                    patch(
                        "ai_labor_atlas.sources.urllib.request.urlopen",
                        return_value=Response(),
                    ),
                ):
                    path = Path(temp) / "baseline.zip"
                    path.write_bytes(b"retained previous baseline")
                    result = download_file(
                        "https://example.test/baseline.zip",
                        path,
                        retries=1,
                        validate_payload=validate_projection_archive,
                    )
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(path.read_bytes(), b"retained previous baseline")

    def test_snapshot_acquisition_is_derived_or_explicitly_unknown(self):
        rows = demo_rows()
        demo = portfolio_snapshot(rows, demo=True)
        self.assertTrue(
            all(
                r["retrieved_at"] is None and r["period"] is None
                for r in demo["records"]
            )
        )
        for row in rows:
            row["wage_vintage"] = "May 2025"
        records = portfolio_snapshot(rows, demo=False)["records"]
        self.assertIsNone(records[0]["retrieved_at"])
        provenance = {
            "generated_at": "2026-11-16",
            "sources": [
                {
                    "source_id": "bls_oews",
                    "retrieved_at": "2026-11-15",
                    "local_modified_at": "2026-11-15",
                }
            ],
        }
        record = portfolio_snapshot(rows, demo=False, build_provenance=provenance)[
            "records"
        ][0]
        self.assertEqual(record["retrieved_at"], "2026-11-15")
        self.assertEqual(record["period"], "2025-05")

    def test_market_snapshot_values_are_strict_and_identity_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            rows = load_market(path)
            source = dict(rows[0])
            for raw in ("20garbage", "nan", "-1"):
                row = {**source, "value": raw}
                write_csv(path / "market_observations.csv", [row], list(row))
                with self.assertRaises(ValueError):
                    load_market(path)
            row = {**source, "value": "1e3"}
            write_csv(path / "market_observations.csv", [row], list(row))
            self.assertEqual(load_market(path)[0]["value"], 1000)
            for field, value in (
                ("schema_version", "wrong"),
                ("period", "2024-13"),
                ("unit", "USD"),
            ):
                broken = {**source, field: value}
                write_csv(path / "market_observations.csv", [broken], list(broken))
                with self.assertRaises(ValueError):
                    load_market(path)

    def test_zero_market_baseline_exports_as_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build_dataset(root / "raw", root / "processed", demo=True)
            result = build_research(root / "raw", root / "processed", root / "research")
        market = result["market_observations"]
        market[0]["value"] = 0
        result["case2"]["market_comparison"] = market_comparison(market)
        self.assertIn("Unavailable (zero baseline)", executive_brief(result))

    def test_staffing_parser_excludes_hierarchy_and_projection_cells(self):
        text = '<table id="mytable"><tr><th>2025 Employment</th></tr>'
        for title, code, kind, base in (
            ("Total", "00-0000", "Summary", "10"),
            ("Group", "15-0000", "Summary", "5"),
            ("Leaf", "15-1252", "Line Item", "3"),
        ):
            text += (
                "<tr>"
                + "".join(
                    f"<td>{x}</td>"
                    for x in (title, code, kind, base, "30", "20", "999")
                )
                + "</tr>"
            )
        text += "</table>"
        records = parse_matrix(text, "540000", "Test", "2026-11-16")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["employment_thousands"], 3)
        rows, total = aggregate_staffing(records)["Test"]
        self.assertEqual(total, 10000)
        self.assertEqual(rows[0]["employment_2024"], 3000)
        with self.assertRaises(ValueError):
            parse_matrix(
                text.replace("2025 Employment", "2026 Employment"),
                "540000",
                "Test",
                "2026-11-16",
            )
        with self.assertRaises(ValueError):
            aggregate_staffing(records + [records[1]])

    def test_industry_denominators_include_suppressed_and_unmatched_employment(self):
        with tempfile.TemporaryDirectory() as temp:
            groups = aggregate_staffing(load_staffing(Path(temp)))
        self.assertEqual(
            set(groups), {"Manufacturing", "Professional and business services"}
        )
        for rows, total in groups.values():
            self.assertGreater(total, 0)
            self.assertLessEqual(
                sum(r["employment_2024"] for r in rows), total * 1.005
            )  # rounded source cells
            self.assertEqual(len(rows), len({r["soc_2018_code"] for r in rows}))

    def test_raw_display_relation_survives_multiple_soc_weighting(self):
        rows = [
            {
                "onet_soc_code": "X",
                "soc_2018_code": "A",
                "crosswalk_weight": 0.25,
                "ai_exposure_source_raw": -1,
                "ai_exposure": 25,
            },
            {
                "onet_soc_code": "X",
                "soc_2018_code": "B",
                "crosswalk_weight": 0.75,
                "ai_exposure_source_raw": 1,
                "ai_exposure": 75,
            },
        ]
        result = aggregate_onet_rows(rows)[0]
        self.assertEqual(result["ai_exposure_source_raw"], 0.5)
        self.assertEqual(result["ai_exposure"], 62.5)

    def test_fixed_display_is_stable_across_subsets_and_retains_signed_raw(self):
        a, b = [{"ai_exposure": -0.5}, {"ai_exposure": 0.6}], [{"ai_exposure": 0.6}]
        _apply_relative_aioe_scale(a, source_bounds=(-2.669758, 1.527667))
        _apply_relative_aioe_scale(b, source_bounds=(-2.669758, 1.527667))
        self.assertEqual(a[1]["ai_exposure"], b[0]["ai_exposure"])
        self.assertEqual(a[0]["ai_exposure_source_raw"], -0.5)
        self.assertTrue(0 <= a[0]["ai_exposure"] <= 100)
        with self.assertRaises(ValueError):
            _apply_relative_aioe_scale(
                [{"ai_exposure": 5}], source_bounds=(-2.669758, 1.527667)
            )

    def test_shared_soc_values_are_counted_once_and_conflicts_rejected(self):
        rows = demo_rows()
        extra = {**rows[0], "onet_soc_code": "15-1252.01"}
        expected = exposure_case(rows)
        actual = exposure_case(rows + [extra])
        self.assertEqual(actual, expected)
        with self.assertRaises(ValueError):
            unique_soc(rows + [{**extra, "employment_2024": 99}])

    def test_missing_exposure_excluded_and_zero_exposure_retained(self):
        rows = demo_rows()
        zero = next(r for r in rows if r["ai_exposure"] == 0)
        self.assertIn(
            zero["soc_2018_code"], [r["soc_2018_code"] for r in unique_soc(rows)]
        )
        rows[0]["ai_exposure"] = None
        self.assertEqual(exposure_case(rows)["sample_soc_count"], 7)
        with self.assertRaises(ValueError):
            exposure_case(rows[:2])

    def test_market_bundle_has_expected_units_and_common_periods(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = load_market(Path(temp))
        result = market_comparison(rows)
        self.assertEqual(len(result), 6)
        self.assertEqual(len({r["end_period"] for r in result}), 1)
        for r in result:
            self.assertAlmostEqual(
                r["change_pct"], 100 * (r["end_value"] / r["start_value"] - 1)
            )

    def test_market_comparison_drops_unmatched_endpoints_and_missing_cells(self):
        rows = []
        for sid, _, _, _, _ in __import__(
            "ai_labor_atlas.intelligence", fromlist=["SERIES"]
        ).SERIES:
            rows += [
                {"source_id": sid, "period": "2024-01", "value": 100},
                {"source_id": sid, "period": "2024-02", "value": 110},
                {"source_id": sid, "period": "2024-03", "value": 130},
            ]
        rows[-1]["value"] = None
        self.assertEqual(
            {r["end_period"] for r in market_comparison(rows)}, {"2024-02"}
        )
        with self.assertRaises(ValueError):
            market_comparison(rows[:3])

    def test_source_parser_rejects_duplicate_wrong_id_and_bad_values(self):
        source = series_manifest()["sources"][0]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.csv"
            for body in (
                "",
                "observation_date,WRONG\n2024-01-01,4\n",
                "observation_date,JTS540099JOL\n2024-01-01,4\n2024-01-01,5\n",
                "observation_date,JTS540099JOL\n2024-01-02,4\n",
                "observation_date,JTS540099JOL\n2024-01-01,nan\n",
            ):
                path.write_text(body)
                with self.subTest(body=body), self.assertRaises(ValueError):
                    parse_series(path, source, "2026-11-16")
            path.write_text(
                "observation_date,JTS540099JOL\n2024-01-01,.\n2024-02-01,0\n"
            )
            result = parse_series(path, source, "2026-11-16")
            self.assertIsNone(result[0]["value"])
            self.assertEqual(result[1]["value"], 0)

    def test_skill_composition_equal_child_then_employment_weighted(self):
        rows = [
            {"soc_2018_code": "15-0001", "onet_soc_code": "A", "employment_2024": 100},
            {"soc_2018_code": "15-0001", "onet_soc_code": "B", "employment_2024": 100},
            {"soc_2018_code": "15-0002", "onet_soc_code": "C", "employment_2024": 300},
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Essential Skills.txt").write_text(
                "O*NET-SOC Code\tScale ID\tElement ID\tElement Name\tData Value\nA\tIM\t2.A.2.a\tCritical Thinking\t1\nB\tIM\t2.A.2.a\tCritical Thinking\t3\nC\tIM\t2.A.2.a\tCritical Thinking\t4\n"
            )
            with patch(
                "ai_labor_atlas.intelligence._load_crosswalk",
                return_value={"A": ["15-0001"], "B": ["15-0001"], "C": ["15-0002"]},
            ):
                result = skill_composition(root, rows, demo=False)
            self.assertEqual(result[0]["importance"], 3.5)  # (100*2 + 300*4) / 400
            self.assertEqual(result[0]["covered_soc_count"], 2)
            self.assertEqual(result[0]["covered_employment_jobs"], 400)

    def test_snapshot_records_nulls_and_native_taxonomies(self):
        rows = demo_rows()
        rows[0]["median_annual_wage"] = None
        snap = portfolio_snapshot(rows, demo=True)
        self.assertEqual(snap["schema_version"], "portfolio.v1")
        self.assertTrue(
            all(r["canonical_id"].startswith("SOC2018:") for r in snap["records"])
        )
        self.assertTrue(any(r["median_annual_wage"] is None for r in snap["records"]))

    def test_offline_research_generates_all_artifacts_and_escapes_embedded_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build_dataset(root / "raw", root / "processed", demo=True)
            result = build_research(root / "raw", root / "processed", root / "research")
            self.assertEqual(result["mode"], "synthetic_occupation_demo")
            self.assertTrue(result["case2"]["bundles"])
            self.assertEqual(len(result["case1"]["quartiles"]), 4)
            result["case1"]["question"] = "</script><script>alert(1)</script>"
            write_research_site(root / "site", result)
            text = (root / "site/index.html").read_text()
            self.assertNotIn("</script><script>alert", text)
            for name in (
                "research.json",
                "executive-brief.md",
                "exposure_quartiles.csv",
                "industry_changes.csv",
                "skill_composition.csv",
                "market_observations.csv",
            ):
                self.assertTrue((root / "site" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
