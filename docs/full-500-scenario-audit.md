# AI Labor Atlas: full 500-scenario audit

This release gate exercises 50 named contract cases through ten controlled variants in [tools/audit_500_atlas_scenarios.py](../tools/audit_500_atlas_scenarios.py). It is a deterministic product and data-contract audit, not a claim that 500 randomly sampled occupations or workers were observed.

## Result

| Check | Result |
| --- | ---: |
| Base contract cases | 50 |
| Variants per case | 10 |
| Total journeys | 500 / 500 |
| Passed | 500 |
| Failed | 0 |
| Unexpected exceptions | 0 |

The 50 cases are balanced across five product surfaces:

| Surface | Journeys | What was checked |
| --- | ---: | --- |
| Summary and data quality | 100 | empty and missing data, non-finite values, shared SOC de-duplication, weighted means, negative market values, and missing mappings |
| Crosswalk weights | 100 | explicit zero, normalization, uniform fallback disclosure, and invalid/negative/non-finite/text weights |
| Occupation mapping | 100 | common titles, editorial candidate families, ambiguous titles, no-match behavior, padding, case changes, and confirmation requirements |
| Public worker-review contract | 100 | field whitelist, PII rejection, date/rating/topic/source validation, length limits, and safe metadata |
| Context and dashboard | 100 | market context, multiple mappings, task filtering/caps, unrelated tasks, missing provenance notices, rank behavior, and demo disclosure |

## Findings and changes

1. Negative AI-exposure, employment, wage, projected-employment, and annual-opening values now fail closed as invalid/missing. Negative employment-change percentages remain valid because they represent contraction rather than an invalid level.
2. Non-finite and invalid crosswalk weights remain rejected; missing allocations use an explicit uniform fallback with a data-quality flag rather than silently selecting a SOC row.
3. Shared SOC targets are deduplicated for release-level employment weighting, while occupation-level output continues to disclose weighted-reference aggregation.
4. Title suggestions and editorial alias candidates remain confirmation-required. Unknown or ambiguous titles return an empty or candidate-family result rather than an automatic occupation classification.
5. Public worker comments use a whitelist and reject email addresses, phone numbers, SSNs, unsupported sources/topics, invalid dates or ratings, overlong excerpts, and missing required fields. Private moderation metadata is not published.
6. A dashboard record with incomplete provenance now shows a data-quality notice instead of looking fully sourced. Demo data remains visibly labeled and is not presented as a labor-market decision basis.

## Product interpretation

The explorer can form a useful descriptive view for an occupation when source coverage exists: tasks remain separate from job requirements, market fields retain their vintages, and the career bridge separates structured distance, software overlap, task evidence, and training hints. It does not produce an individual career recommendation, ability estimate, hiring probability, wage-causality claim, or job-loss probability.

The main remaining user-facing limitations are intentional: U.S. national English-language coverage, release-vintage lag, partial occupation/task coverage, ambiguous nonstandard titles, and the need for a user to confirm any occupation mapping. Public worker comments add context only; they do not become a rating or change Atlas measures.

## Verification commands

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m compileall -q src tests tools
python tools/audit_500_atlas_scenarios.py
```
