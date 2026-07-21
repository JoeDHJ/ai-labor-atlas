# Design

The pipeline has four layers:

1. **Acquire**: download or register official files and write SHA-256 checksums.
2. **Validate**: check expected files, row counts, unique keys, and value parsability.
3. **Build**: normalize O*NET, bridge to 2018 SOC, and left-join wage, projections, and exposure data.
4. **Explore**: expose search and descriptive summaries through the CLI and a dependency-free local HTML page.

Every output row includes source/version fields or can be traced to `data_manifest.json`. Data are stored as CSV for portability and JSON for metadata.

