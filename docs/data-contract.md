# Data contract

The canonical occupation output contains:

```text
onet_soc_code
soc_2018_code
crosswalk_weight
title
description
ai_exposure
ai_exposure_display_scale
ai_exposure_source
ai_exposure_soc_vintage
employment_2024
projected_employment_2024_thousands
projected_employment_2034_thousands
employment_change_2024_2034_pct
annual_openings_2024_2034
median_annual_wage
onet_version
wage_vintage
projection_vintage
crosswalk_method
data_quality_flags
```

Missing values remain blank and are accompanied by coverage fields. A blank exposure is not a zero exposure. A blank wage is not a zero wage.

Units:

- `ai_exposure`: a bounded 0--100 relative display of source AIOE values. It preserves the source ordering within a release, but is not a probability of job loss, a replacement-risk percentage, or a forecast. It is never negative. AIOE uses SOC 2010 while Atlas market data use SOC 2018: Atlas classifies every row in the complete official BLS crosswalk, keeps only unmarked one-to-one relationships, and leaves every split/merge mapping missing with `aioe_crosswalk_ambiguous` rather than inventing an allocation.
- `ai_exposure_display_scale`: `relative_0_100_min_max` when a source AIOE value is available. The release manifest records the signed-source minimum, maximum, and interpretation needed to reproduce this display transform from the registered AIOE source.
- `ai_exposure_soc_vintage`: the source-to-target SOC bridge used for the AIOE value. `2010_to_2018_official_bridge` signals the conservative BLS bridge; split and merged occupations remain missing instead of receiving an invented allocation.
- `employment_2024`: workers from national OEWS. Negative values are treated as invalid/missing.
- `projected_employment_2024_thousands` and `projected_employment_2034_thousands`: thousands of workers from BLS projections; negative values are treated as invalid/missing.
- `annual_openings_2024_2034`: workers per year; converted from the BLS table's thousands unit. Negative values are treated as invalid/missing.
- `median_annual_wage`: U.S. dollars for the stated wage vintage; negative values are treated as invalid/missing.
- `employment_change_2024_2034_pct`: negative values remain valid because they represent contraction rather than an invalid level.
- If a dashboard record lacks a source version, vintage, crosswalk method, or exposure source, the page displays a data-quality notice instead of silently presenting it as fully provenanced data.
- `crosswalk_weight`: explicit weight for a source O*NET occupation's mapped 2018 SOC rows. When the official crosswalk supplies no allocation, the build uses a uniform weight across that occupation's target SOC rows and records the limitation in `data_quality_flags`.

The raw CSV preserves one row per O*NET-to-SOC mapping. Consumers that need one record per O*NET occupation should use the published aggregation contract: numeric market fields are crosswalk-weighted means, `mapping_status` identifies `multiple_soc_crosswalk`, and `soc_2018_codes` lists all target codes. This is a reference estimate, not a direct SOC observation. When the source crosswalk has several targets but no allocation, every expanded row carries `uniform_crosswalk_fallback`; consumers must disclose that limitation. A shared SOC target across multiple O*NET occupations is flagged as `shared_soc_crosswalk`. An occupation without a usable target carries `missing_crosswalk` and `mapping_status: missing_soc_mapping`; it must not be described as a single-SOC observation. Non-finite crosswalk weights are rejected rather than silently treated as missing.

The task catalog is stored separately in `tasks.csv`:

```text
onet_soc_code
task_id
task_statement
task_type
incumbents_responding
task_date
domain_source
onet_version
source_file
task_quality_flags
```

Task statements describe representative work activities for an occupation. They are not individual job requirements and do not imply that every worker performs every task.

## Career bridge response

The local server exposes `GET /api/bridge?source=<O*NET-SOC code>`. The response contains:

- `source`: the selected occupation and its labor-market snapshot;
- `candidates`: adjacent occupations with `structured_distance`, `structured_similarity`, `software_overlap`, `task_similarity`, `shared_profile_elements`, `shared_task_evidence`, `training_hint`, and `confidence`;
- `method`: the source files, weighting boundary, and interpretation caveat;
- `available` and an explicit error message when the structured O*NET files are not present.

The primary distance uses weighted normalized importance ratings from O*NET Essential Skills, Transferable Skills, Knowledge, Abilities, and Work Activities. Software overlap is a separate set-overlap signal and lightly regularizes the ranking. Task-text overlap is supplemental evidence only. A `family_average` profile is used only when the parent O*NET code has no direct structured rating and is visibly labeled.

The response supports pathway discovery. It does not estimate individual ability, hiring probability, wage causality, or future employment. Title suggestions normalize simple singular and plural forms, require compatible role terms, and require all non-role query terms to appear in the title. The service returns no candidate rather than using a generic token such as `machine`, `manager`, or `analyst` as a standalone match. A small editorial alias registry in `config/occupation_aliases_en.json` can return multiple candidate occupation families for common nonstandard titles. These candidates have `match_score: null`, `mapping_status: candidate_family`, an explicit `mapping_note`, and always require user confirmation.

The full-data build validates every alias candidate code against the current O*NET release before writing the processed release. Serving a non-demo release performs the same fail-closed check. A demo release is intentionally allowed to be partial; an alias can therefore be recognized while returning an empty candidate list, which clients must describe as a data-coverage limitation rather than a failed title match.

## Worker review context response

The local server exposes `GET /api/reviews?occupation=<O*NET-SOC code>` and `GET /api/occupation-context?source=<O*NET-SOC code>`. The latter combines the selected occupation row with the review context used by Career Fit. A title-only suggestion endpoint is available at `GET /api/occupation-context?query=<text>`; it always returns `requires_confirmation: true`.

The review object uses schema `occupation_reviews.v0.1` and contains `review_id`, `onet_soc_code`, `source`, optional `source_url`, `review_scope`, optional `review_date`, optional context fields, `topics`, optional `rating`, and `excerpt`. The response includes source counts and topic counts for navigation only. It deliberately has no sentiment score, average rating, representativeness estimate, or truth label.

Reviews are user-generated and may be incomplete, subjective, outdated, or biased. They are not verified facts or representative of all workers. Source links and dates are shown where available. Reviews are contextual comments, not a measurement input, and do not change Atlas indicators or Career Fit scores.

The release check `atlas validate-reviews --input <path>` returns a JSON import report with `valid`, `row_count`, `normalized_row_count`, `invalid_row_count`, `duplicate_review_ids`, `occupation_codes`, `source_counts`, `topic_counts`, and field-level `errors`. The report never prints review excerpts. A file is ready for the dashboard only when `valid` is `true`.

## Market context response

`GET /api/occupation-context?source=<O*NET-SOC code>` also returns `market_context.v0.2`. It keeps the selected occupation's `metrics`, `provenance`, `mapping`, `representative_tasks`, and `adjacent_occupations` separate from worker comments. The metrics are descriptive snapshots; AI exposure is shown as a 0--100 relative display rather than a job-loss probability, wage levels are not causal effects, and adjacent occupations are not personal recommendations. The provenance fields preserve O*NET, wage, projection, exposure, and crosswalk vintages for downstream consumers. When several SOC targets are attached to one O*NET occupation, `mapping.status` is `multiple_soc_crosswalk` and the metrics disclose the weighted-reference method. Its `mapping.data_quality_flags` carries fallback and shared-target warnings. The release-level `employment_weighted_exposure` is weighted over unique 2018 SOC units (`employment_weighting_unit: unique_soc_2018`) so shared SOC employment is not counted once per O*NET source row.

The release summary reports `rows`, `unique_onet_occupation_count`, `aggregated_onet_occupation_count`, `unique_soc_count`, `crosswalk_expanded_row_count`, `crosswalk_expanded_onet_count`, `employment_weighting_unit`, `employment_weighting_row_count`, `shared_soc_count`, `conflicting_soc_count`, and `multiple_soc_occupation_count`. Coverage and means use one aggregated record per O*NET occupation, while employment-weighted exposure uses one collapsed record per unique SOC target. The raw row and crosswalk counts remain available for auditability; consumers should not describe raw `rows` as a count of independent occupations. The dashboard chart is explicitly an O*NET view; its bubble employment is not the unique-SOC KPI.
