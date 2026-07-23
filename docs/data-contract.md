# Data contract

The canonical occupation output contains:

```text
onet_soc_code
soc_2018_code
title
description
ai_exposure
ai_exposure_source
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

- `ai_exposure`: source exposure score; it is not a probability of job loss.
- `employment_2024`: workers from national OEWS.
- `projected_employment_2024_thousands` and `projected_employment_2034_thousands`: thousands of workers from BLS projections.
- `annual_openings_2024_2034`: workers per year; converted from the BLS table's thousands unit.
- `median_annual_wage`: U.S. dollars for the stated wage vintage.

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
