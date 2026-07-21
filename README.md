# AI Labor Atlas

AI Labor Atlas is a reproducible, descriptive measurement layer connecting occupations, tasks, AI exposure indicators, wages, and employment projections.

The first release is intentionally narrow: U.S. national data, English sources, and no causal claims. It keeps source taxonomies and data vintages explicit so that future updates can be compared rather than silently replacing earlier results.

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

The demo build is deterministic and creates a small local dataset. For the public sources, inspect `config/source_registry.json`, place downloaded files in `data/raw/`, and run `atlas build`.

## Visual demo

Run `python -m ai_labor_atlas.cli build --demo` and then `python -m ai_labor_atlas.cli serve`. Open `http://127.0.0.1:8765` to explore the local dashboard.

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
