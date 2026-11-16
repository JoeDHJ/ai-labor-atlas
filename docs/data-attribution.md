# Data attribution and transformation ledger

AI Labor Atlas 0.6.1 · Haojian Dui · retrieved 16 November 2026

Atlas code is MIT licensed. Incorporated research data retain the separate source
licenses below; the code license does not relicense those data. No private
conversations, user identifiers or individual employment records are included.

## Microsoft Working with AI

Tomlinson, Kiran; Jaffe, Sonia; Wang, Will; Counts, Scott; and Suri, Siddharth.
*Working with AI: Measuring the Applicability of Generative AI to Occupations*.
[Official results](https://github.com/microsoft/working-with-ai), v1.1,
repository revision `550c00c9d1b054ac78b87da3a26165bace334779`.

Licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
Used: occupation applicability, activity metrics, task physical classifications,
SOC/activity links, original and nonphysical activity weights. The original
repository notice attributes underlying O*NET 29.0 and BLS materials. This project
adds rank comparisons, score reconstruction and a task-text benchmark. It does
not imply endorsement by Microsoft or the source authors.

The source describes US Bing Copilot conversations from 1 January to 30 September
2024. Classifier-derived completion, scope and coverage enter the applicability
score. These measures do not estimate the capacity to replace an entire job.

## Anthropic Economic Index

Handa, Kunal, et al. *Which Economic Tasks are Performed with AI? Evidence from
Millions of Claude Conversations*. [Official initial release](https://huggingface.co/datasets/Anthropic/EconomicIndex/tree/main/release_2025_02_10),
10 February 2025. Dataset repository revision
`4e5f69fab13a9c3f7d0dcc31a6f893a9818738f6`.

The release README explicitly says **data CC-BY, code MIT**; the CC-BY version is
not specified there. The dataset card's MIT metadata is not treated as overriding
that data-specific statement. Retained attribution and the published public-use
designation govern the included aggregates. Used: task conversation percentages
and accompanying task statements. Transformations: case/whitespace normalization,
official crosswalk composition, equal fractional allocation across target SOCs,
rank conversion and occupation aggregation. The source observation dates are not
specified in these CSVs; the release date is not presented as an observation date.

The released `none` task label represents 0.481557% of conversation share and has
no O*NET task-statement match. Atlas retains it in the total-share denominator and
does not allocate it to an occupation. This is a source residual category, not an
unexplained fuzzy-match failure. Newer Economic Index releases exist; this project
uses a pinned historical comparison without treating releases as a harmonized panel.

## O*NET

O*NET is sponsored by the U.S. Department of Labor, Employment and Training
Administration, and developed by the National Center for O*NET Development.
O*NET® is a trademark of USDOL/ETA. Used under CC BY 4.0.

- [Official O*NET-SOC 2010 → 2019 crosswalk](https://www.onetcenter.org/taxonomy/2019/walk.html), retrieved 16 November 2026.
- [O*NET-SOC 2019 → SOC 2018 crosswalk](https://www.onetcenter.org/taxonomy.html), retained local official workbook acquired in July 2026.
- [O*NET 29.0](https://www.onetcenter.org/dl_files/database/db_29_0_text.zip), task text for the physical/nonphysical benchmark when rebuilding from original sources.
- O*NET 30.3 for the existing occupation explorer and skill analysis, as documented in the original source registry.

Atlas modifies these materials by joining, normalizing, aggregating, ranking and
classifying. Taxonomy crosswalks describe possible occupational correspondence;
they do not reveal the actual occupation behind an AI conversation. Source-native
task IDs and unique text units are kept distinct in the measurement exercise.

## AIOE and BLS/FRED

[Felten, Raj and Seamans, AIOE](https://github.com/AIOE-Data/AIOE) is retained locally
for aggregate indicator comparisons. Occupation-level exposure values are excluded
from bundled public data while redistribution licensing remains unverified. The
public packet includes only descriptive aggregate comparisons, with definitions
and sample counts.

Monthly data are from the U.S. Bureau of Labor Statistics via the Federal Reserve
Bank of St. Louis FRED service, retrieved 16 November 2026. The warehouse includes
JOLTS openings and CES payroll employment and nominal hourly earnings for
professional/business services and manufacturing. Source-native IDs, units and
observation dates remain attached. Industry-series endpoint SQL uses each source's
own first and last observed months; the prior market report instead uses common
months across all six series. They answer different endpoint comparisons.

## Reproduction and provenance

`tools/acquire_comparison_sources.py --anthropic-revision <pinned revision>`
explicitly downloads the public comparison inputs and records URLs, release labels,
retrieval times and file sizes. It does not run on serving. The local acquisition
manifest stays in `data/raw/comparison/manifest.json`. The bundled
`measurement_snapshot.json` retains that manifest; the legacy crosswalk and O*NET
29.0 benchmark acquisition are recorded separately in its additional-source records.
`tools/build_research_workbench.py` builds the selected public packet. No file
hashes or private source records are required for reproduction.
