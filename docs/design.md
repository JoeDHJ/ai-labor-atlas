# Design

The pipeline has four layers:

1. **Acquire**: download or register official files and write SHA-256 checksums.
2. **Validate**: check expected files, row counts, unique keys, and value parsability.
3. **Build**: normalize O*NET, bridge to 2018 SOC, and left-join wage, projections, and exposure data.
4. **Explore**: expose search and descriptive summaries through the CLI and a dependency-free local HTML page.
5. **Bridge**: compare structured O*NET occupational profiles and return separate software and task evidence for pathway discovery.

Every output row includes source/version fields or can be traced to `data_manifest.json`. Data are stored as CSV for portability and JSON for metadata.

The bridge layer follows a task-based, multidimensional interpretation of occupational mobility. It uses weighted normalized distances across O*NET Essential Skills, Transferable Skills, Knowledge, Abilities, and Work Activities as the primary signal. Software overlap and shared task statements remain separate evidence. The result is a descriptive occupation bridge, not an estimate of a particular worker's ability or hiring outcome.

The applied design is informed by [Gathmann and Schönberg](https://www.journals.uchicago.edu/doi/full/10.1086/649786), [Poletaev and Robinson](https://www.journals.uchicago.edu/doi/10.1086/588180), and the [OECD occupation-distance study](https://doi.org/10.1787/d35017ee-en). These sources motivate task-based transfer and training interpretation; they do not validate the bridge as an individual recommendation model.
