# Official employer requirements → delivered evidence

Checked 2026-11-16. These are role benchmarks, not applications, endorsements,
claims of prior employment or a statement that every qualification is satisfied.
Requirements below are paraphrased from official employer descriptions.

| Official description | Requirements relevant to Atlas | Inspectable evidence | Boundary |
| --- | --- | --- | --- |
| [Amazon Economist II, AMZ27751.1, Job 10514197](https://www.amazon.jobs/en/jobs/10514197/economist-ii-amz27751-1) | Build economic models, process large datasets, use time-series/panel methods, present analysis to management | `intelligence.py` ingests and validates source identities, aligns time windows, deduplicates occupation keys and regenerates two cases; `scenario.py` documents capacity accounting; executive brief/report and downloadable dashboard tables communicate decisions | Atlas demonstrates descriptive measurement and scenario accounting. It does not claim to demonstrate causal program evaluation or a validated forecast. The JD's PhD/experience/SQL requirements are not certified by this product. |
| [Amazon Sr. Economist, WW Prime, Job 10598358](https://www.amazon.jobs/en/jobs/10598358/sr-economist-ww-prime) | Translate a business question into an analytic vision; use economic data systems and statistical software; address quantitative problems and automated workflows | Question → source → measure → exhibit → decision chain in the research report; Python CLI and source manifests; actual market observations and industry staffing; scenario sensitivity, clean distribution checks and CI | This is independent public-data portfolio work, not a paid client engagement or production deployment at Amazon. |

The first description explicitly requests written/presented analysis for different
management levels; the second describes quantitative work with management,
scientists and engineers. Atlas supplies both a short decision brief and a detailed
methods report, with executable outputs a technical reviewer can inspect.

## Reviewer navigation

| Capability | Artifact | Acceptance |
| --- | --- | --- |
| Public data engineering | `config/market_manifest.json`, packaged source registries, `staffing.py` | Six monthly source identities, four industry matrices, dates/units/row counts, candidate validation and version review |
| Economic measurement | `pipeline.py`, `intelligence.py` | Raw/display AIOE distinction, conservative cross-version bridge, one market observation per SOC, explicit coverage denominators |
| Applied labor analysis | `docs/reports/labor-market-intelligence.md` | Two actual public-data cases, nominal wage interpretation, vacancies distinct from employment, source and population boundaries |
| Workforce decisions | `scenario.py`, dashboard | Baseline, adoption path, task shares, training cost/effectiveness, horizon, annual capacity and sensitivity |
| Professional delivery | README, executive brief, figures, `docs/demo-script.md` | A hiring manager can reach question, result, chart, methods and runnable workflow in two minutes |
| Reliable software | `tests/`, CI and release evidence | Calculation/edge checks, original workflows, clean wheel/sdist runtime, browser and independent review |
