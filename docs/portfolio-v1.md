# portfolio.v1: Atlas public analytical snapshots

Atlas owns occupation/skill/market measurements. No sibling service is required
to generate or consume the exports. `atlas research` writes the local occupation
adapter at `data/research/portfolio_snapshot.json`; the dashboard's research JSON
and CSV downloads provide public case aggregates and monthly observations.

## Occupation snapshot

One record per unique target occupation. `canonical_id = SOC2018:<code>` and
`source_native_id` retain the source key. `taxonomy` and `taxonomy_vintage` are
explicit. `onet_titles` lists attached O*NET child titles; `title` is a representative
child label and is **not** represented as an official SOC title.

Required source metadata includes `source_id`, `source_url`, `retrieved_at`,
`source_vintage`, `geography`, `unit_of_observation`, `period`, `currency`,
`price_year`, `schema_version` and `status`. Source wage/employment observations
are separate from estimated AIOE exposure. The source AIOE value and 0–100 display
are both retained. Crosswalk method and quality flags are supplied, including
ambiguous/missing source mappings. Unavailable numeric cells are JSON `null`.

The source API's legacy `employment_2024` name is retained for compatibility in
`occupations.csv` and existing endpoints. It contains OEWS May 2025 employment.
New consumers use `employment_jobs` and `period: 2025-05`. Do not compare this
value directly with the BLS projection model's 2024 employment baseline.

Shared O*NET child occupations do not multiply employment. Conflicting market
values within one SOC fail analysis. Multiple target mappings remain expanded in
the original occupation CSV. Research skill cases accept only single-target
O*NET mappings, average observed children equally within SOC, and weight SOCs
by the named employment source. No undocumented source allocation is inferred.

## Skills and industries

`skill_composition.csv` carries O*NET element IDs, labels, taxonomy/version, IM
scale, covered/all code counts, covered employment, coverage ratio and the
employment weighting source. `research.json` additionally carries skill-pair
co-occurrence and the 3.5/5 threshold. A co-occurrence share is not a return to
combining skills or a transition probability.

Industry staffing records use BLS National Employment Matrix 2025 codes, aligned
to SOC 2018 where an exact key exists. BLS aggregates that have no exact O*NET
target remain unmatched. NAICS 54,55,56 are disjoint and summed for professional
and business services; manufacturing is 31–33. Published totals are coverage
denominators, so suppressed/poor-quality/small cells are not silently removed from
the denominator or reconstructed. Only baseline employment is imported.

Monthly records retain the FRED-native series ID and BLS supersector grouping,
period, source vintage, retrieval date, seasonal adjustment, status and units.
The comparison window is the intersection of nonmissing periods in all six
series. CES jobs, JOLTS openings and hourly USD are distinct units.

## Consumer example

```python
import json
from pathlib import Path

snapshot = json.loads(Path("data/research/portfolio_snapshot.json").read_text(encoding="utf-8"))
assert snapshot["schema_version"] == "portfolio.v1"
occupations = {record["canonical_id"]: record for record in snapshot["records"]}
record = occupations.get("SOC2018:15-1252")
if record and record["median_annual_wage"] is not None:
    print(record["median_annual_wage"], record["period"], record["status"])
```

Consumers should keep a dated local snapshot and display its provenance. Do not
silently substitute an occupation, zero-fill missing observations, or treat the
scenario output as an observed forecast. AIOE occupation-level redistribution
rights remain unverified; the generated full occupation adapter stays local.
