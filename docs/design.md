# Design

The pipeline has four layers:

1. **Acquire**: download or register official files and write SHA-256 checksums.
2. **Validate**: check expected files, row counts, unique keys, and value parsability.
3. **Build**: normalize O*NET, bridge to 2018 SOC, store explicit crosswalk weights, and left-join wage, projections, and exposure data.
4. **Explore**: expose search and descriptive summaries through the CLI and a dependency-free local HTML page.
5. **Bridge**: compare structured O*NET occupational profiles and return separate software and task evidence for pathway discovery.

Every output row includes source/version fields or can be traced to `data_manifest.json`. Data are stored as CSV for portability and JSON for metadata.

The raw release keeps one row per O*NET-to-SOC mapping. Summary statistics and occupation context collapse those rows to one O*NET record using the stored crosswalk weights, disclose when several SOC targets are involved, and retain the raw expansion counts. Because the public bridge does not provide a defensible individual allocation, the result is a weighted reference estimate rather than a direct SOC statistic. The release-level employment-weighted exposure is calculated after collapsing shared targets to one record per unique 2018 SOC code, preventing BLS employment from being duplicated across O*NET mappings; fallback allocations are flagged in the data-quality contract.

The bridge layer follows a task-based, multidimensional interpretation of occupational mobility. It uses weighted normalized distances across O*NET Essential Skills, Transferable Skills, Knowledge, Abilities, and Work Activities as the primary signal. Software overlap and shared task statements remain separate evidence. The result is a descriptive occupation bridge, not an estimate of a particular worker's ability or hiring outcome.

The applied design is informed by [Gathmann and Schönberg](https://www.journals.uchicago.edu/doi/full/10.1086/649786), [Poletaev and Robinson](https://www.journals.uchicago.edu/doi/10.1086/588180), and the [OECD occupation-distance study](https://doi.org/10.1787/d35017ee-en). These sources motivate task-based transfer and training interpretation; they do not validate the bridge as an individual recommendation model.

## Release validation

Every release candidate runs 50 maintained contract cases through ten controlled variants. The audit keeps source parsing, crosswalk arithmetic, title mapping, public-review safety, and dashboard disclosure separate so a passing summary statistic cannot mask a failing user-facing contract. A release is not considered complete when a field merely parses; it must also preserve missingness, provenance, confirmation boundaries, and the product's descriptive interpretation.
