# Data acquisition

The repository intentionally does not commit raw occupational data. Run the following locally:

```powershell
python -m pip install -e ".[excel]"
python -m ai_labor_atlas.cli download
python -m ai_labor_atlas.cli build
python -m ai_labor_atlas.cli analyze
```

The downloader records results in `data/download_manifest.json`. If BLS blocks automated requests, download the May 2025 national OEWS file and the official 2024-2034 projections table from the BLS pages listed in `config/source_registry.json`, then save them as:

- `data/raw/bls_oews_may_2025.zip` or `data/raw/bls_oews.csv`
- `data/raw/bls_projections_2024_2034.xlsx` or `data/raw/bls_projections_2024_2034.csv`

The build will preserve missingness and report coverage. Do not replace missing values with zero.

The full-source parser reads the national OEWS workbook inside the official May 2025 ZIP and Table 1.2 of the official projections workbook. BLS annual openings are stored as workers in the canonical output; the source table reports that field in thousands, so the build multiplies it by 1,000. The local validation snapshot produced 1,016 occupation rows with no duplicate O*NET/SOC output pairs.
