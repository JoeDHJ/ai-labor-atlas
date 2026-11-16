# AI Labor Atlas — Tasks, Evidence & Organization

**Release 0.6.0 · Independent portfolio research by Haojian Dui**

Which tasks deserve an AI pilot, and how should training and task allocation change
when drafting becomes faster? Atlas connects labor-market measurement to a
transparent organizational decision.

**[Open the live public-data case →](https://joedhj.github.io/ai-labor-atlas/)**
No installation, account, API key or private data required. Search 758 occupations,
inspect their task evidence, compare six organization alternatives and export the
current assumptions. The case also works offline after export.

- **Measurement:** Copilot applicability and task-linked Claude conversation share
  share 100 of 190 top-quartile picks on a common sample of 758 SOC occupations.
  Official taxonomy crosswalks preserve 99.52% of released task share; source
  residuals and allocation sensitivity remain visible. These are different
  descriptive measures, not job-loss probabilities.
- **Organization:** a hypothetical research-team case counts review bottlenecks,
  error rework, a quality floor, training time, role qualification and recruitment
  delay. Under the default assumptions, AI plus training produces 493.3 expected
  accepted briefs versus 521.6 at baseline; adding qualified task reallocation
  raises expected output to 665.7. These are model outputs, not firm treatment effects.
- **Professional practice:** reproducible Python/SQL analysis, numerical reconstruction
  of 785 published scores, grouped held-out task classification against silver
  labels, and a browser calculator checked against the Python model.

Start with the [research brief](docs/research-brief.md),
[capability evidence and interview guide](docs/career-evidence.md),
[full assumptions](docs/workflow-assumptions.md), or
[three-round review record](docs/review-0.6.0.md).
The existing [market, wage and skill research](docs/reports/labor-market-intelligence.md)
and occupation explorer remain available.

![AI Labor Atlas research workbench](docs/assets/atlas-workbench-0.6.jpg)

## Reproduce the real public-data case

Requires Python 3.10 or newer; the core has no external dependencies.

```powershell
python -m pip install ai-labor-atlas==0.6.0
atlas workbench --output my-research
atlas workflow --demand-per-week 30 --output my-research/low-demand.json
```

Open `my-research/index.html` in a browser. The export contains the actual public
aggregate case, offline interactions, CSV/JSON data, SQL queries and a SQLite
warehouse. `atlas workflow --help` lists model inputs, including the qualification
and recruitment delays. Source acquisition never happens during rendering.

To add the original local explorer and market research:

```powershell
python -m pip install "ai-labor-atlas[excel]==0.6.0"
atlas download
atlas build
atlas research
atlas serve
```

The local homepage links to the market workspace and its occupation explorer.
For an explicitly synthetic occupation fixture, use `atlas build --demo`; the new
workbench always uses its separately labeled actual public aggregates. Atlas reads
occupation data under the current directory's `data/`, or the directory specified
by `AI_LABOR_ATLAS_DATA_DIR`. `atlas workbench --output` uses its explicit output path.

For source-level reproduction and the selected evidence boundary, see
[reproduction instructions](docs/reproduction.md) and
[data attribution](docs/data-attribution.md). Maintainer publication instructions
are in [docs/publishing.md](docs/publishing.md).

## Explore the dashboard

The dashboard brings occupational tasks, AI exposure, wages, employment, and outlook together in one visual workspace for comparing roles and exploring changing work. The screenshots below are rendered from the full current-data build (1,016 O*NET occupation records), not the eight-record demonstration dataset.

![AI Labor Atlas occupation and task explorer](docs/assets/atlas-explorer.jpg)

The dashboard compares AI exposure with wages, projected employment growth, annual openings, and employment scale. It pairs the visual comparison with plain-language metric guidance so users can explore the economic context behind each occupation.

The Career bridge view helps users explore adjacent occupations. It uses structured O*NET importance ratings as the primary profile distance, then shows software overlap, supplemental task evidence, labor-market context, and a practical training hint. The bridge is a descriptive pathway tool. It is not a personal ability estimate, a hiring-probability model, or an employment forecast.

### Optional semantic review

The dashboard can send one selected occupation and its deterministic mapping to an OpenAI-compatible chat-completions endpoint for a second, text-based review. The review is advisory: it cannot change the dataset, exposure values, SOC codes, or summary measures. Leave the variables unset to keep the dashboard fully local and rule-based.

```powershell
$env:AI_LABOR_ATLAS_LLM_API_KEY = "your-key"
$env:AI_LABOR_ATLAS_LLM_BASE_URL = "https://api.openai.com/v1"
$env:AI_LABOR_ATLAS_LLM_MODEL = "your-model"
atlas serve
```

The selected occupation and deterministic mapping evidence are sent only when
the review button is used. A local OpenAI-compatible endpoint may be used
without an API key.

## Data sources and vintages

| Layer | Source | Version/vintage | Use |
| --- | --- | --- | --- |
| Occupation and tasks | O*NET | 30.3 | O*NET-SOC titles, descriptions, tasks, skills, software skills |
| Occupation bridge | O*NET crosswalk | 2019 -> 2018 SOC | Join O*NET occupations to BLS data |
| Wage | BLS OEWS | May 2025 | National employment and wage estimates |
| Outlook | BLS Employment Projections | 2024-2034 | Employment change and annual openings |
| AI exposure | AIOE | source release recorded in manifest | Descriptive exposure comparator |
| Monthly demand | BLS JOLTS via FRED | retrieved 2026-11-16; Jan 2022–Sep 2026 | Unfilled positions, two industry groups |
| Monthly employment/pay | BLS CES via FRED | retrieved 2026-11-16; Jan 2022–Oct 2026 | Payroll jobs and nominal hourly earnings |
| Industry staffing | BLS National Employment Matrix | 2025 baseline from 2025–2035 release | Industry-weighted occupational skills; projected cells excluded |

O*NET-derived files must retain attribution to O*NET and the U.S. Department of Labor, Employment and Training Administration, and must identify modifications. AIOE raw redistribution is disabled by default until its repository license is verified.

The full local build uses the registered public files rather than the demo rows.
The retained occupation baseline contains 1,016 unique O*NET occupations and
18,796 source task statements across 923 occupations, with **79.6% exposure
coverage (809/1,016)**, 94.1% wage coverage, and 94.6% employment coverage.
The earlier README's 79.0% was incorrect and was reproduced and corrected in this
release. Occupation baseline files were acquired in July 2026; their vintages stay
explicit even as monthly market data are updated. The legacy 2024–2034 outlook
is a retained official projection vintage, not the newest BLS projection release.
Release summaries distinguish unique O*NET occupations, unique SOC codes, raw
crosswalk-expanded rows, and one-record-per-O*NET coverage. Research calculations
deduplicate SOC market quantities. Missing source values remain missing.

The occupation bridge uses O*NET 30.3 Essential Skills, Transferable Skills, Knowledge, Abilities, Work Activities, and Software Skills. Exact profiles are preferred; when a parent occupation has no direct structured rating, a family-average profile is marked in the result. This fallback is a data-coverage aid, not an exact occupational equivalence.

### What workers say

The occupation detail view includes an optional space for public worker comments about pay, interviews, management, workload, growth, and work environment. Comments keep their source, date, scope, and link where available. They are displayed as context rather than combined into an overall rating, and they never change the Atlas measures.

To load an auditable local import, create `data/processed/reviews.json` using the contract in [docs/review-data.md](docs/review-data.md). The demo does not invent worker comments. Review imports must respect the source platform's current terms, API rules, attribution requirements, privacy obligations, and user-content rights.

Before starting the dashboard, run the release check against an import file. It reports every row-level error and the resulting occupation, source, and topic coverage without printing review text:

```powershell
python -m ai_labor_atlas.cli validate-reviews --input data/processed/reviews.json
```

The dashboard remains fail-closed: a file that does not pass this check is not partially displayed.

Career Fit can connect to this context through the Atlas server. Set `CAREER_FIT_ATLAS_URL=http://127.0.0.1:8765` before starting Career Fit, then confirm the closest standard occupation in its optional occupation-context panel. Title suggestions are deliberately non-binding because a job title can map to several occupations.

Occupation suggestions use normalized title phrases and compatible role terms. If the supplied title is too broad or does not map cleanly to an Atlas title, the explorer returns no suggestion and asks the user to try a more specific title. This favors a transparent empty result over a plausible but misleading occupation.

For a small set of common nonstandard titles, the versioned [editorial candidate crosswalk](config/occupation_aliases_en.json) provides multiple possible occupation families. These are leads for user review, not official O*NET equivalences or automatic classifications; each candidate includes a mapping note and requires confirmation.

The research rationale and application boundaries are summarized in [the literature-to-product map](docs/literature-map.md).

The full `50 × 10 = 500` deterministic scenario audit, including data-quality, crosswalk, mapping, public-review, and dashboard checks, is documented in [the full audit report](docs/full-500-scenario-audit.md).

## What the numbers mean

`ai_exposure` is an exposure/applicability indicator, not a probability of job loss,
a risk score, or evidence of causality. Its fixed public-build transform is
`100 × (ai_exposure_source_raw + 2.669758) / (1.527667 + 2.669758)`.
Signed source values stay in `ai_exposure_source_raw`; subsetting does not rescale
the display. Values outside this fixed source range require vintage review.

Crosswalk-expanded rows retain `crosswalk_weight` and quality flags. Multiple
targets use disclosed weighted references; research skill cases exclude multi-target
O*NET ratings instead of inventing allocations. Market quantities enter once per
SOC. The legacy `employment_2024` field contains OEWS May 2025 employment;
the new [portfolio.v1 adapter](docs/portfolio-v1.md) exports `employment_jobs`
with an explicit period. Source records use versions, dates, sizes and schemas.

Research exports are written to `data/research/`, including the local downstream
occupation snapshot, two case tables, skills, monthly observations and Markdown
brief. AIOE occupation values are not bundled in distributions because upstream
redistribution rights remain unverified. Published case aggregates are in
`docs/reports/`; full locally generated source/occupation outputs remain local.

## Repository map

- `src/ai_labor_atlas/`: loaders, joins, measures, CLI, and local dashboard
- `config/source_registry.json`: source URLs, versions, licenses, and redistribution status
- `docs/`: requirements, design, and data contract
- `tests/`: deterministic unit tests
