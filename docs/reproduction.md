## Real-data workbench added in 0.6.0

The real public-data case can be exported without downloading any source files or
building the synthetic occupation fixture:

```powershell
atlas workbench --output my-research
atlas workflow --demand-per-week 30 --output my-research/low-demand.json
```

Open `my-research/index.html` directly, or serve that folder with an ordinary static
web server. All interactions run locally; the site does not call the legacy Python
scenario API. `research.sqlite` contains source, occupation, source-specific metric,
task, task usage, fractional occupation/task links and monthly observation tables.
`research-queries.sql` executes against that schema. Each monthly series retains
its own source units and dates; its SQL endpoint query differs deliberately from
the older six-series common-month case.

For source-level regeneration from a clone:

```powershell
python -m pip install -e ".[excel,reports]"
atlas download
atlas build
python tools/acquire_comparison_sources.py --anthropic-revision 4e5f69fab13a9c3f7d0dcc31a6f893a9818738f6
python tools/build_research_workbench.py
python tools/build_workbench_figures.py
```

The source-level public build requires a `public_raw` occupation manifest and
rejects the synthetic fixture. It regenerates public aggregates and keeps AIOE
occupation values local. Source files, exact revisions, transformations and data
licenses are described in `data-attribution.md`. The grouped benchmark uses the
official O*NET 29.0 task statements and published physical-task labels; all identical
normalized text stays in one split. The human review queue is pending.

The web bundle in `docs/` is a selected evidence packet. It contains licensed public
aggregates, a model contract and hypothetical scenarios; it excludes raw AI
conversations, AIOE occupation values and private records. Existing reports under
`docs/reports/` retain their original source vintages. New 300 dpi PNG and editable
SVG figures are `indicator-ranks` and `workflow-capacity`.

# Reproduce the 0.5.0 workspace

## Clean offline demonstration

From any empty working directory after installing `ai-labor-atlas[excel]==0.5.0`:

```powershell
atlas build --demo
atlas research
atlas scenario --years 3
atlas serve
```

Open `http://127.0.0.1:8765`. Occupations/skills are labeled synthetic. The
packaged monthly and staffing observations remain actual public BLS data.
The demo does not assert actual occupation-level case findings.

## Actual public-data cases

```powershell
atlas download
atlas build
atlas research
atlas analyze
atlas serve
```

Registered sources: O*NET 30.3 text database, O*NET-SOC2019→SOC2018 crosswalk,
AIOE appendix, OEWS May 2025 national workbook and retained BLS 2024–2034
occupation projection workbook. These occupation files were acquired locally in
July 2026 and the release was regenerated from them on 16 November 2026. Source
filenames/landing links are in `config/source_registry.json`. A direct ZIP request
to BLS can return HTTP 403 in some environments; the downloader reports that
specific failure and preserves existing local files. Obtain the official file
through its public landing page when needed. No authentication bypass is used.

Monthly and industry baseline observations ship with their source manifests so
the historical case remains reproducible when official websites change. To fetch
a new explicit retrieval vintage:

```powershell
atlas market-update
atlas staffing-update
atlas research
```

An unsuccessful source refresh leaves the previously published complete output
panel intact. Raw candidates may remain for inspection. Existing source files
keep one `.previous` business version. The staffing parser requires a 2025
baseline header; a future vintage needs an explicit adapter review.

## Outputs and units

- `data/processed/occupations.csv`: crosswalk rows; signed raw and fixed 0–100
  display AIOE; legacy API fields retained.
- `data/research/research.json`: two complete cases and their public source data.
- `exposure_quartiles.csv`: one SOC counted once; nominal annual wage levels.
- `industry_changes.csv`: one common monthly window; changes in percent.
- `skill_composition.csv`: IM importance on its 1–5 source scale; per-skill coverage.
- `portfolio_snapshot.json`: local `portfolio.v1` occupation adapter with nulls,
  exact IDs, source dates and observed/estimated/synthetic status.
- `executive-brief.md`: rendered from the same results object as the dashboard.

All research paths above are under `data/research/` unless otherwise specified.
Use `AI_LABOR_ATLAS_DATA_DIR` to select another data directory. Do not commit the
full local occupation snapshot while AIOE redistribution rights are unverified.

## Rebuild report exhibits from a clone

```powershell
python -m pip install -e ".[excel,reports]"
atlas research
python tools/build_portfolio_evidence.py
```

This intentionally copies selected aggregates instead of the full analysis
directory. It creates Markdown, CSV, JSON, PNG and SVG only. Report text and
source/method notes are in `docs/reports/labor-market-intelligence.md`.

## Validation

```powershell
python -m unittest discover -s tests -v
python -m ruff check .
python tools/audit_500_atlas_scenarios.py
python -m build
```

CI checks Python 3.10–3.14, the established 500-scenario audit and installed wheel
and source-distribution workflows outside the source tree. Release verification
also exercises both research cases, scenario arithmetic, malformed inputs,
browser comparison controls, exports and responsive layouts. See the final
implementation/review records for actual outcomes rather than treating this
command list as proof that checks passed.
