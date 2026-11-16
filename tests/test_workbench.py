from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from ai_labor_atlas.comparison import (
    allocate_tasks,
    analyze_snapshot,
    fractional_ranks,
    load_snapshot,
)
from ai_labor_atlas.research_sql import build_warehouse
from ai_labor_atlas.resources import resource_path
from ai_labor_atlas.workbench import write_workbench
from ai_labor_atlas.workflow import Workflow, run_workflow


class ComparisonTests(unittest.TestCase):
    def test_fractional_join_deduplicates_children_and_conserves_source_residual(self):
        statements = [
            {"O*NET-SOC Code": c, "Task": "Do task.", "Title": c}
            for c in ("old1", "old2", "old3")
        ]
        mapping = [
            {"task_name": " DO TASK. ", "pct": "70"},
            {"task_name": "none", "pct": "30"},
        ]
        result = allocate_tasks(
            mapping,
            statements,
            {"old1": ["11-1011"], "old2": ["11-1011"], "old3": ["13-1111"]},
        )
        self.assertEqual(
            [r["claude_share_pct"] for r in result["occupations"]], [35, 35]
        )
        self.assertEqual(result["join"]["unmatched_share_pct"], 30)
        self.assertEqual(result["join"]["allocated_share_pct"], 70)

    def test_ties_use_average_percentile_and_constant_is_not_a_correlation(self):
        self.assertEqual(
            fractional_ranks({"a": 0, "b": 0, "c": 2}), {"a": 25, "b": 25, "c": 100}
        )
        with self.assertRaises(ValueError):
            fractional_ranks({"a": math.nan})

    def test_duplicate_usage_is_rejected(self):
        with self.assertRaises(ValueError):
            allocate_tasks(
                [{"task_name": "A", "pct": 1}, {"task_name": "a", "pct": 1}], [], {}
            )

    def test_public_snapshot_has_no_aioe_values_and_conserved_mass(self):
        snapshot = load_snapshot()
        self.assertEqual(snapshot["common_count"], len(snapshot["occupations"]))
        j = snapshot["join"]
        self.assertAlmostEqual(
            j["allocated_share_pct"] + j["unmatched_share_pct"], j["released_share_pct"]
        )
        self.assertTrue(all("aioe_raw" not in r for r in snapshot["occupations"]))
        self.assertTrue(
            all(r["ms_applicability"] is not None for r in snapshot["occupations"])
        )

    def test_sql_ranks_match_python_with_ties_and_mass_is_conserved(self):
        with tempfile.TemporaryDirectory() as temp:
            sql = build_warehouse(Path(temp) / "research.sqlite")
            a = analyze_snapshot(load_snapshot())
            expected = sorted(
                a["occupations"], key=lambda r: (-abs(r["rank_gap_pp"]), r["soc"])
            )[:12]
            self.assertEqual(
                [r["soc"] for r in sql["largest_rank_gaps"]],
                [r["soc"] for r in expected],
            )
            for actual, row in zip(sql["largest_rank_gaps"], expected):
                self.assertAlmostEqual(actual["gap_pp"], row["rank_gap_pp"])
            mass = sql["task_mass_conservation"][0]
            self.assertAlmostEqual(mass["source_matched_pct"], mass["allocated_pct"])

    def test_real_workbench_build_requires_no_local_occupation_files(self):
        with tempfile.TemporaryDirectory() as temp:
            result = write_workbench(Path(temp))
            self.assertGreater(result["common_soc_count"], 700)
            text = (Path(temp) / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("__ATLAS_DATA__", text)
            self.assertTrue((Path(temp) / "research.sqlite").exists())
            self.assertIn("public_aggregate_data", text)


class WorkflowTests(unittest.TestCase):
    def test_quality_gate_demand_limit_and_training_reallocation(self):
        result = run_workflow()
        rows = {r["id"]: r for r in result["strategies"]}
        self.assertFalse(rows["ai_only"]["quality_eligible"])
        self.assertLess(
            rows["train"]["accepted_cases"], rows["baseline"]["accepted_cases"]
        )
        self.assertEqual(result["best_strategy"], "redesign")
        self.assertTrue(
            all(
                r["completed_cases"] <= result["parameters"]["demand_per_week"]
                for s in result["strategies"]
                for r in s["trajectory"]
            )
        )

    def test_low_demand_prefers_existing_workflow(self):
        self.assertEqual(
            run_workflow(replace(Workflow(), demand_per_week=30))["best_strategy"],
            "baseline",
        )

    def test_quality_threshold_and_long_recruitment_delay(self):
        for error, eligible in ((0.20, True), (0.201, False)):
            r = run_workflow(replace(Workflow(), trained_error_rate=error))
            self.assertEqual(
                next(
                    s["quality_eligible"] for s in r["strategies"] if s["id"] == "train"
                ),
                eligible,
            )
        r = run_workflow(replace(Workflow(), hiring_lead_weeks=20))
        baseline, hire = r["strategies"][0], r["strategies"][4]
        self.assertEqual(hire["accepted_cases"], baseline["accepted_cases"])
        self.assertEqual(hire["incremental_cash_cost"], 2500)

    def test_training_never_creates_negative_capacity(self):
        r = run_workflow(
            replace(Workflow(), analyst_hours_per_week=1, reviewer_hours_per_week=1)
        )
        for s in r["strategies"]:
            self.assertTrue(
                all(
                    x["analyst_capacity"] >= 0 and x["reviewer_capacity"] >= 0
                    for x in s["trajectory"]
                )
            )

    def test_reallocation_waits_for_qualification(self):
        result = run_workflow()
        trained, redesign = result["strategies"][2:4]
        self.assertEqual(
            trained["trajectory"][0]["reviewer_capacity"],
            redesign["trajectory"][0]["reviewer_capacity"],
        )
        self.assertGreater(
            redesign["trajectory"][2]["reviewer_capacity"],
            trained["trajectory"][2]["reviewer_capacity"],
        )
        delayed = run_workflow(replace(Workflow(), reallocation_delay_weeks=20))[
            "strategies"
        ][3]
        self.assertLess(delayed["accepted_cases"], redesign["accepted_cases"])

    def test_invalid_inputs_fail_without_undefined_outputs(self):
        for change in (
            {"weeks": 1},
            {"weeks": 2.5},
            {"demand_per_week": 0},
            {"trained_error_rate": 1.01},
            {"ai_review_hours": math.nan},
            {"value_per_accepted_case": 10**400},
            {"hiring_lead_weeks": True},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run_workflow(replace(Workflow(), **change))

    @unittest.skipUnless(
        shutil.which("node"), "Node unavailable; Python model still tested"
    )
    def test_browser_matches_python_for_material_counterfactuals(self):
        cases = [
            Workflow(),
            replace(Workflow(), demand_per_week=30),
            replace(Workflow(), demand_per_week=90, ai_review_hours=0.8),
            replace(Workflow(), trained_error_rate=0.2),
            replace(Workflow(), trained_error_rate=0.201, hiring_lead_weeks=104),
            replace(Workflow(), analyst_hours_per_week=1, reviewer_hours_per_week=1),
        ]
        command = [
            "node",
            "-e",
            'require(process.argv[1]); let s=""; process.stdin.on("data",x=>s+=x); process.stdin.on("end",()=>process.stdout.write(JSON.stringify(JSON.parse(s).map(globalThis.runWorkflow))));',
            str(resource_path("workbench.js")),
        ]
        actual = json.loads(
            subprocess.run(
                command,
                input=json.dumps([asdict(p) for p in cases]),
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )
        for p, browser in zip(cases, actual):
            expected = run_workflow(p, False)
            self.assertEqual(expected["best_strategy"], browser["best_strategy"])
            for a, b in zip(expected["strategies"], browser["strategies"]):
                for key in (
                    "accepted_cases",
                    "quality_pass_rate",
                    "cash_cost",
                    "incremental_contribution",
                ):
                    self.assertAlmostEqual(a[key], b[key], places=7)


if __name__ == "__main__":
    unittest.main()
