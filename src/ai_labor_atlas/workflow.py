"""Finite-horizon task bottleneck and personnel decision model.

All organization parameters are hypothetical. No empirical treatment effect is assumed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Workflow:
    demand_per_week: float = 60
    value_per_accepted_case: float = 350
    analyst_hours_per_week: float = 30
    reviewer_hours_per_week: float = 30
    ai_review_hours: float = 1.2
    trained_error_rate: float = 0.12
    hiring_lead_weeks: int = 6
    reallocation_delay_weeks: int = 2
    weeks: int = 12

    def validate(self):
        for key, value in asdict(self).items():
            try:
                valid = not isinstance(value, bool) and math.isfinite(value)
            except (TypeError, OverflowError):
                valid = False
            if not valid:
                raise ValueError(f"{key} must be finite")
        for key in ("hiring_lead_weeks", "reallocation_delay_weeks", "weeks"):
            value = getattr(self, key)
            if not isinstance(value, int) or not 0 <= value <= 104:
                raise ValueError(f"{key} must be an integer from 0 to 104")
        if self.weeks < 2:
            raise ValueError("weeks must be at least 2")
        if self.reallocation_delay_weeks < 2:
            raise ValueError("reallocation_delay_weeks must be at least 2")
        if not 0 <= self.trained_error_rate <= 1:
            raise ValueError("trained_error_rate must be in [0,1]")
        for key in (
            "demand_per_week",
            "value_per_accepted_case",
            "analyst_hours_per_week",
            "reviewer_hours_per_week",
            "ai_review_hours",
        ):
            if not 0 < getattr(self, key) <= 1_000_000:
                raise ValueError(f"{key} must be positive and at most 1,000,000")


STRATEGIES = [
    ("baseline", "Current workflow"),
    ("ai_only", "AI without training"),
    ("train", "AI + role-specific training"),
    ("redesign", "AI + training + task reallocation"),
    ("hire_analyst", "Recruit one analyst"),
    ("hire_reviewer", "AI + training + recruit one reviewer"),
]


def evaluate(p: Workflow, strategy: str) -> dict:
    if strategy not in dict(STRATEGIES):
        raise ValueError("Unknown strategy")
    ai = strategy in {"ai_only", "train", "redesign", "hire_reviewer"}
    trained = strategy in {"train", "redesign", "hire_reviewer"}
    error = p.trained_error_rate if trained else (0.25 if ai else 0.10)
    # One rework pass: 90% of initially erroneous cases corrected; residuals retained.
    quality = 1 - error * 0.10
    required_a = 6 + (40 / p.reallocation_delay_weeks if strategy == "redesign" else 0)
    feasible = not trained or (
        p.analyst_hours_per_week >= required_a and p.reviewer_hours_per_week >= 4
    )
    analyst_unit = 0.5 + (0.9 + 0.8 if ai else 1.5 + 2.0) + error * 1.0
    review_unit = p.ai_review_hours if trained else (1.6 if ai else 1.2)
    review_unit += (0.15 if trained else (0.25 if ai else 0.05)) + error * 0.5
    trajectory = []
    for week in range(1, p.weeks + 1):
        moved = strategy == "redesign" and week > p.reallocation_delay_weeks
        analysts, reviewers = (5, 3) if moved else (6, 2)
        hired = week > p.hiring_lead_weeks
        a = analysts + int(strategy == "hire_analyst" and hired)
        r = reviewers + int(strategy == "hire_reviewer" and hired)
        # Initial staff train during weeks 1 and 2; the extra reviewer is assumed prequalified.
        training_a = analysts * 6 if trained and week <= 2 else 0
        training_r = reviewers * 4 if trained and week <= 2 else 0
        # Additional role qualification for the employee who will move, beyond AI training.
        if strategy == "redesign" and week <= p.reallocation_delay_weeks:
            training_a += 40 / p.reallocation_delay_weeks
        ac = max(0, a * p.analyst_hours_per_week - training_a) / analyst_unit
        rc = max(0, r * p.reviewer_hours_per_week - training_r) / review_unit
        attempts = min(ac, rc, p.demand_per_week)
        bottleneck = (
            "demand"
            if p.demand_per_week <= min(ac, rc)
            else ("analyst" if ac <= rc else "reviewer")
        )
        extra_salary = (
            (900 if strategy == "hire_analyst" else 1400)
            if hired and strategy.startswith("hire_")
            else 0
        )
        cost = 8200 + (400 if ai else 0) + extra_salary
        if week == 1:
            cost += (2000 if trained else 0) + (
                2500 if strategy.startswith("hire_") else 0
            )
        trajectory.append(
            {
                "week": week,
                "analyst_capacity": ac,
                "reviewer_capacity": rc,
                "completed_cases": attempts,
                "accepted_cases": attempts * quality,
                "bottleneck": bottleneck,
                "cash_cost": cost,
            }
        )
    accepted = sum(r["accepted_cases"] for r in trajectory)
    cost = sum(r["cash_cost"] for r in trajectory)
    return {
        "id": strategy,
        "label": dict(STRATEGIES)[strategy],
        "quality_pass_rate": quality,
        "quality_eligible": quality >= 0.98 - 1e-12,
        "feasibility_eligible": feasible,
        "accepted_cases": accepted,
        "cash_cost": cost,
        "contribution": accepted * p.value_per_accepted_case - cost,
        "analyst_hours_per_case": analyst_unit,
        "reviewer_hours_per_case": review_unit,
        "steady_bottleneck": trajectory[-1]["bottleneck"],
        "trajectory": trajectory,
    }


def run_workflow(p: Workflow = Workflow(), include_sensitivity: bool = True) -> dict:
    p.validate()
    strategies = [evaluate(p, key) for key, _ in STRATEGIES]
    base = strategies[0]
    for row in strategies:
        row["incremental_accepted_cases"] = (
            row["accepted_cases"] - base["accepted_cases"]
        )
        row["incremental_cash_cost"] = row["cash_cost"] - base["cash_cost"]
        row["incremental_contribution"] = row["contribution"] - base["contribution"]
        gain = row["incremental_accepted_cases"]
        row["break_even_value_per_case"] = (
            row["incremental_cash_cost"] / gain if gain > 0 else None
        )
    eligible = [
        r for r in strategies if r["quality_eligible"] and r["feasibility_eligible"]
    ]
    best = max(eligible, key=lambda r: r["contribution"]) if eligible else None
    result = {
        "schema": "atlas.workflow.v1",
        "status": "hypothetical_decision_model",
        "parameters": asdict(p),
        "strategies": strategies,
        "best_strategy": best["id"] if best else None,
        "quality_floor": 0.98,
    }
    if include_sensitivity:
        result["sensitivity"] = []
        for demand in (30, 60, 90):
            for review in (0.8, 1.2, 1.6):
                scenario = run_workflow(
                    replace(p, demand_per_week=demand, ai_review_hours=review), False
                )
                result["sensitivity"].append(
                    {
                        "demand_per_week": demand,
                        "ai_review_hours": review,
                        "best_strategy": scenario["best_strategy"],
                    }
                )
    return result
