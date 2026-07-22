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
