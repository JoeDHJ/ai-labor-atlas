# AI Labor Market Intelligence

Haojian Dui · Release 0.5.0 · US national public data

## Decision brief

Use occupational exposure to choose workflows for evaluation, then use demand and skill evidence to set training priorities.

Across 691 complete SOC occupations, the highest exposure quartile has an employment-weighted average occupational median wage of $88,489, compared with $45,686 in the lowest quartile (1.94 times; Table I). This is a wage-level comparison, not an AI wage effect.

AIOE covers 809 of 1,016 O*NET occupations (79.6%). Unmatched observations remain missing.

## Table I. Wage and employment by AI exposure quartile

| Exposure quartile | SOC count | Employment, millions | Weighted occupation median, USD/year |
| --- | ---: | ---: | ---: |
| 1 | 172 | 31.54 | 45,686 |
| 2 | 173 | 27.20 | 49,998 |
| 3 | 173 | 38.88 | 68,160 |
| 4 | 173 | 31.09 | 88,489 |

Notes: Employment-weighted average of occupation medians, not the median wage of all workers. OEWS May 2025; nominal USD/year. Sampling covariance is unavailable; no inferential or causal claim is made. SOCs enter once. Quartiles contain equal numbers of occupations, with code order breaking exposure ties. The sample excludes 176 SOCs with missing exposure, wage or positive employment.

## Table II. Industry labor-market change

| Industry | Measure | First month | Last common month | Change, percent |
| --- | --- | --- | --- | ---: |
| Professional and business services | job openings | 2022-01 | 2026-09 | -37.3 |
| Manufacturing | job openings | 2022-01 | 2026-09 | -34.7 |
| Professional and business services | payroll employment | 2022-01 | 2026-09 | +1.6 |
| Manufacturing | payroll employment | 2022-01 | 2026-09 | +0.8 |
| Professional and business services | hourly earnings | 2022-01 | 2026-09 | +21.7 |
| Manufacturing | hourly earnings | 2022-01 | 2026-09 | +21.4 |

Notes: BLS JOLTS openings and CES employment/earnings via FRED; monthly, seasonally adjusted. Endpoints use the same months across all six series. Earnings are nominal; no inflation adjustment is implied. Openings are unfilled positions at month end; payroll employment counts jobs. Source estimates can be revised. CES composition changes can affect average earnings.

## Table III. Critical Thinking and Active Listening skill bundle

| Group | Both importance ratings at least 3.5/5, covered employment | Employment coverage |
| --- | ---: | ---: |
| Computer and mathematical | 67.9% | 100.0% |
| Office and administrative support | 11.0% | 97.9% |
| Production | 10.6% | 94.9% |
| Manufacturing (industry) | 31.0% | 85.8% |
| Professional and business services (industry) | 50.5% | 91.2% |

Notes: O*NET 30.3 IM importance ratings; exact children averaged equally within SOC. National families use OEWS May 2025 employment; industries use the BLS 2025 staffing baseline. Professional/business services sums disjoint NAICS 54,55,56; manufacturing uses 31–33. Industry coverage uses published totals, including unmatched and suppressed cells. Co-occurrence does not establish economic complementarity.

## Action

Evaluate a bounded task workflow before purchasing broad training. Pair analytical skills with communication and domain judgment, and validate the relevant occupation's exact ratings in the explorer. Use the scenario tool to compare adoption and training assumptions in hours of capacity; retain headcount as a separate organizational decision.

## Evidence and reproduction

`atlas research` regenerates both cases and the structured tables. `atlas market-update` explicitly refreshes six registered public series. `atlas scenario --help` documents the scenario inputs.

Sources: [BLS OEWS](https://www.bls.gov/oes/tables.htm), [O*NET 30.3](https://www.onetcenter.org/database.html), [AIOE](https://github.com/AIOE-Data/AIOE), [BLS JOLTS via FRED](https://fred.stlouisfed.org/series/JTS540099JOL), [CES via FRED](https://fred.stlouisfed.org/series/USPBS), [BLS industry matrix](https://data.bls.gov/projections/nationalMatrix?queryParams=540000&ioType=i).
