# AI Labor Atlas 0.6.0

A real-data research workbench for labor economics, organizational design and AI.

- Compare 758 common SOC occupations across Microsoft Copilot applicability and
  fractionally allocated Anthropic task-use aggregates, with official taxonomy
  bridges, mass conservation, source definitions and rank sensitivity.
- Inspect a separate 692-occupation AIOE comparison without redistributing
  occupation-level AIOE values.
- Compare six hypothetical training, task-reallocation and recruitment strategies,
  including review bottlenecks, rework, qualification delay, training time and a
  quality floor. Export current assumptions and weekly outcomes.
- Build an offline real-data site and SQLite warehouse with `atlas workbench`;
  run the personnel model with `atlas workflow`.
- Reconstruct all 785 published applicability scores; evaluate physical-task text
  classification with grouped held-out data and explicitly labeled silver labels.
- Read a research brief, model contract, source/attribution ledger, standalone
  figures, capability matrix and interview guide. Existing market research and
  occupation/task explorer remain accessible through local serving.

Validation: 97 unit checks, the maintained 500-scenario audit, lint/compilation,
Python/browser numerical agreement, desktop/mobile interaction, and clean wheel
and source-distribution installations. See `docs/review-0.6.0.md` for actual scope
and remaining substantive limits.

The empirical comparisons are descriptive. Organization outputs are hypothetical;
no causal workplace productivity effect or independent human annotation is claimed.

Live case: https://joedhj.github.io/ai-labor-atlas/
