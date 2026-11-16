# Data acquisition

The repository intentionally does not commit raw occupational data. Run the following locally:

```powershell
python -m pip install -e ".[excel]"
python -m ai_labor_atlas.cli download
python -m ai_labor_atlas.cli build
python -m ai_labor_atlas.cli analyze
```

The downloader records source URLs, versions, dates, paths and byte sizes in
`data/download_manifest.json`. It preserves one previous local business version.
Empty or non-ZIP payloads for a ZIP destination fail without replacing the file.
The separate monthly/staffing refreshers validate source identity, duplicate
keys, numeric cells and vintage before publishing a complete output panel.
If BLS blocks automated requests, obtain the May 2025 national OEWS file and the
retained official 2024–2034 projections table from the BLS pages listed in
`config/source_registry.json`, then save them as:

- `data/raw/bls_oews_may_2025.zip` or `data/raw/bls_oews.csv`
- `data/raw/bls_projections_2024_2034.xlsx` or `data/raw/bls_projections_2024_2034.csv`
- `data/raw/bls_projections_2024_2034_archive.zip` is the pinned download from
  the official BLS historical archive. The parser reads its nested `occupation.xlsx`.

The build will preserve missingness and report coverage. Do not replace missing values with zero.

The full-source parser reads the O*NET occupation and task files, the national
OEWS workbook inside the official May 2025 ZIP, and Table 1.2 of the retained
projections workbook. BLS projected annual openings are stored as jobs/year; the
source reports thousands, so the build multiplies by 1,000. The validation
snapshot has 1,016 unique O*NET occupations and 18,796 task rows.

`atlas market-update` refreshes the six executable entries in
`config/market_manifest.json`. `atlas staffing-update` refreshes four industry
matrix pages, imports their 2025 baseline only, and rejects an unexpected vintage.
Packaged public snapshots support offline reproduction. See
[reproduction.md](reproduction.md) for commands, paths and the data boundary.
