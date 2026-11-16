"""Transparent capacity accounting; parameters are user assumptions, not forecasts."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Scenario:
    workforce: float = 1000
    years: int = 3
    annual_adoption: float = 0.25
    automation_task_share: float = 0.15
    augmentation_task_share: float = 0.25
    automation_saving: float = 0.60
    augmentation_saving: float = 0.20
    training_hours: float = 24
    training_effectiveness: float = 0.50
    hours_per_worker: float = 2000

    def validate(self) -> None:
        for key, value in asdict(self).items():
            try:
                valid = (
                    not isinstance(value, bool)
                    and isinstance(value, (float, int))
                    and math.isfinite(value)
                )
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{key} must be a finite number")
        if not isinstance(self.years, int) or not 1 <= self.years <= 20:
            raise ValueError("years must be an integer from 1 to 20")
        if not 0 < self.workforce <= 1e9 or not 0 < self.hours_per_worker <= 8760:
            raise ValueError(
                "workforce and hours_per_worker must be positive and within bounds"
            )
        if not 0 <= self.training_hours <= self.hours_per_worker:
            raise ValueError(
                "training_hours must be between zero and annual work hours"
            )
        for key in (
            "annual_adoption",
            "automation_task_share",
            "augmentation_task_share",
            "automation_saving",
            "augmentation_saving",
            "training_effectiveness",
        ):
            if not 0 <= getattr(self, key) <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
        if self.automation_task_share + self.augmentation_task_share > 1:
            raise ValueError(
                "automation and augmentation task shares must sum to at most 1"
            )


def run_scenario(params: Scenario) -> dict:
    params.validate()
    trajectory, previous = [], 0.0
    for year in range(1, params.years + 1):
        adoption = 1 - (1 - params.annual_adoption) ** year
        automation = (
            params.workforce
            * params.hours_per_worker
            * adoption
            * params.automation_task_share
            * params.automation_saving
        )
        augmentation = (
            params.workforce
            * params.hours_per_worker
            * adoption
            * params.augmentation_task_share
            * params.augmentation_saving
            * params.training_effectiveness
        )
        training = params.workforce * (adoption - previous) * params.training_hours
        net = automation + augmentation - training
        trajectory.append(
            {
                "year": year,
                "adoption_share": adoption,
                "automation_capacity_hours": automation,
                "augmentation_capacity_hours": augmentation,
                "training_hours": training,
                "net_capacity_hours": net,
                "fte_equivalent_capacity": net / params.hours_per_worker,
                "workforce_baseline": params.workforce,
                "status": "scenario",
            }
        )
        previous = adoption
    return {
        "schema_version": "portfolio.v1",
        "status": "scenario",
        "parameters": asdict(params),
        "trajectory": trajectory,
        "interpretation": "Capacity hours relative to a constant workforce and workload baseline. FTE-equivalent capacity divides hours by annual hours per worker; it is not a headcount reduction, hiring forecast or causal effect. Task shares and savings are user assumptions, independent of AIOE. Training is incurred once per new adopter; effectiveness scales augmentation savings.",
    }


def sensitivity(params: Scenario) -> list[dict]:
    result = []
    for label, speed in (
        ("slower", params.annual_adoption * 0.5),
        ("base", params.annual_adoption),
        ("faster", min(1, params.annual_adoption * 1.5)),
    ):
        output = run_scenario(replace(params, annual_adoption=speed))
        result.append(
            {"case": label, "annual_adoption": speed, **output["trajectory"][-1]}
        )
    return result
