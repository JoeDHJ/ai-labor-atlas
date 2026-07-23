# Requirements

## Intent

Provide an auditable public tool for exploring how occupational AI exposure indicators line up with tasks, wages, employment, and projected growth.

## Functional requirements

1. Use explicit source versions and retain a provenance manifest.
2. Use O*NET-SOC 2019 as the source occupation code and preserve the official bridge to 2018 SOC.
3. Join national OEWS May 2025 and BLS 2024-2034 projections where a valid SOC key exists.
4. Treat AIOE as an exposure/applicability measure and preserve missingness.
5. Support deterministic demo data, public-data download, validation, build, search, analysis, and local serving.
6. Preserve every crosswalk row, store an explicit mapping weight, aggregate multiple SOC targets only through a disclosed weighted-reference contract, and report coverage without silently selecting one row.
7. Provide a descriptive Career bridge that ranks adjacent occupations using structured O*NET profile distance.
8. Expose software overlap, shared task evidence, profile provenance, labor-market context, and a training hint separately.
9. Mark family-average fallbacks and unavailable structured profiles explicitly.
10. Run a repeatable 50-case by 10-variant release audit covering measurement, crosswalks, occupation mapping, public review validation, and dashboard provenance disclosure; publish the result with the release evidence.

## Non-goals for 0.1

- causal effects, job-loss probabilities, or firm-level AI response;
- individual career recommendations;
- worker ability estimates, hiring-probability rankings, or employment forecasts;
- China, multilingual data, or live job-board scraping;
- redistribution of sources whose license is not verified.
