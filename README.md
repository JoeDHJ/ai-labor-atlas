# AI Labor Atlas

AI Labor Atlas is a reproducible, descriptive measurement layer connecting occupations, tasks, AI exposure indicators, wages, and employment projections.

The current explorer focuses on U.S. national data, English-language sources, and descriptive—not causal—interpretation. It keeps the meaning and coverage of each measure clear so users can ask better questions about changing work.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[excel]"
python -m ai_labor_atlas.cli build --demo
python -m ai_labor_atlas.cli analyze
python -m ai_labor_atlas.cli search analyst
python -m ai_labor_atlas.cli serve
```

The demonstration dataset is deterministic so the examples are easy to explore and reproduce. Research users can find the public source coverage and attribution notes in the sections below.

## Explore the dashboard

The dashboard connects occupational tasks, AI exposure, wages, employment, and projections in one visual view. Run the project locally to explore the interactive experience.

![AI Labor Atlas dashboard](docs/assets/atlas-dashboard.png)

The dashboard compares AI exposure with wages, projected employment growth, annual openings, and employment scale. Exposure is a task-applicability indicator—not a probability of job loss—so the page explains the economic meaning and limits of each measure alongside the chart.

## Data sources and vintages

| Layer | Source | Version/vintage | Use |
| --- | --- | --- | --- |
| Occupation and tasks | O*NET | 30.3 | O*NET-SOC titles, descriptions, tasks, skills, software skills |
| Occupation bridge | O*NET crosswalk | 2019 -> 2018 SOC | Join O*NET occupations to BLS data |
| Wage | BLS OEWS | May 2025 | National employment and wage estimates |
| Outlook | BLS Employment Projections | 2024-2034 | Employment change and annual openings |
| AI exposure | AIOE | source release recorded in manifest | Descriptive exposure comparator |

O*NET-derived files must retain attribution to O*NET and the U.S. Department of Labor, Employment and Training Administration, and must identify modifications. AIOE raw redistribution is disabled by default until its repository license is verified.

## What the numbers mean

`ai_exposure` is an exposure/applicability indicator, not a probability of job loss, a risk score, or evidence of causality. Wage and employment projections are joined by SOC code with provenance and coverage fields. Many-to-one crosswalks are preserved and summarized rather than silently collapsed.

## Repository map

- `src/ai_labor_atlas/`: loaders, joins, measures, CLI, and local dashboard
- `config/source_registry.json`: source URLs, versions, licenses, and redistribution status
- `docs/`: requirements, design, and data contract
- `tests/`: deterministic unit tests
