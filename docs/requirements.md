# Requirements

## Intent

Provide an auditable public tool for exploring how occupational AI exposure indicators line up with tasks, wages, employment, and projected growth.

## Functional requirements

1. Use explicit source versions and retain a provenance manifest.
2. Use O*NET-SOC 2019 as the source occupation code and preserve the official bridge to 2018 SOC.
3. Join national OEWS May 2025 and BLS 2024-2034 projections where a valid SOC key exists.
4. Treat AIOE as an exposure/applicability measure and preserve missingness.
5. Support deterministic demo data, public-data download, validation, build, search, analysis, and local serving.
6. Preserve many-to-one crosswalks and report coverage instead of silently selecting one row.

## Non-goals for 0.1

- causal effects, job-loss probabilities, or firm-level AI response;
- individual career recommendations;
- China, multilingual data, or live job-board scraping;
- redistribution of sources whose license is not verified.

