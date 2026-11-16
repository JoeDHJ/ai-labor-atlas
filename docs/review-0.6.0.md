# Three-round review and optimization: 0.6.0

Owner: Haojian Dui Â· 16 November 2026 Â· Branch `codex/research-workbench-0.6.0`

This record covers implementation review, automated calculation checks and actual
browser interaction. These rounds were performed in the development session;
they are not independent external peer review or a human annotation study.
Existing unrelated `output/` files were preserved.

## Round 1: economic question, sources and measurement

**Finding:** The accompanying Anthropic task file uses legacy O*NET-SOC codes.
Connecting it directly to the current taxonomy lost much of the task usage share.
**Fix:** Compose official O*NET-SOC 2010 â†’ 2019 â†’ SOC 2018 crosswalks. Normalize
only case and whitespace in task wording. Divide each shared task's released
share equally across distinct target SOCs, without multiplying by child records.

**Verified outcome:** 3,513 matched task labels out of 3,514; matched conversation
share 99.518443%. The remaining 0.481557% is the source's explicit `none` category.
758 SOC occupations have both public indicators, including 171 with zero matched
released usage; missing source coverage remains missing. Top-quartile overlap is
100 of 190. Allocation sensitivity and the 587-occupation positive-use restriction
are reported, with their different denominators.

**Knowledge-depth optimization:** Preserve each source's construct, platform,
vintage and unit. AIOE compares on a separate 692-occupation three-source sample,
with all three pairs calculated on that sample. Public data contain aggregate AIOE
comparisons only. The report distinguishes applicability, potential exposure,
platform conversation share, workplace adoption and job displacement.

## Round 2: personnel model, measurement evaluation and interaction

**Finding:** Immediate reassignment to review overstated qualification readiness.
**Fix:** Add 40 hours of role qualification and a two-week delay before moving the
employee. Exclude alternatives whose per-person time cannot fit planned training.
Keep training capacity and cash cost separate to avoid counting salary twice.

**Verified outcome:** The default hypothetical baseline yields 521.6 expected
accepted briefs over 12 weeks. Training alone yields 493.3; qualified reallocation
yields 665.7, with USD 43,639 incremental modeled contribution at the assumed value.
At demand 30, the current workflow is preferred. The untrained AI alternative fails
the 98% quality floor. The report never treats these outputs as measured firm effects.

**Finding:** Task IDs alone can put identical wording in training and holdout.
**Fix:** Group normalized identical wording before splitting, use official O*NET
29.0 text, and learn the vocabulary only from training data. Retain source labels
unchanged, including conflicting labels within 16 wording groups.

**Verified outcome:** 15,051 training and 3,745 held-out task IDs, zero exact text
overlap; Naive Bayes balanced agreement 85.9%, keyword rule 60.2%, majority 50.0%.
Labels are published LLM silver labels. A 40-case human review queue remains pending.
All 785 published applicability scores reconstruct within 1eâˆ’10 tolerance.

**UX optimization:** The page uses real public aggregates on first opening.
Occupation search, empty search, a keyboard-accessible selector, chart selection,
default/reset controls and low-demand decision reversal were exercised in Chrome.
Editing assumptions disables export and marks results stale until recalculation.
Browser and Python model calculations agree on material counterfactuals.

**Presentation optimization:** Use a question-led first screen, a compact result
card, source/task inspection and an explicit author contribution. Mobile navigation
shows all four destinations; mobile chart labels were enlarged. At 390 px width,
the page had no horizontal body overflow; wide tables scroll inside their panels.
Desktop and mobile screenshots are saved without opening files for the user.

## Round 3: professional evidence, reproducibility and delivery

**Capability evidence:** The public research brief, SQL database and queries,
grouped measurement benchmark, model contract, standalone 300 dpi PNG/SVG figures,
and 30-second/three-minute/15-minute interview guides support the target careers.
Official Anthropic and Amazon requirements were checked directly. Academic
qualifications, client experience and causal research are not inferred from delivery.

**Professional checks:** The warehouse keeps source-specific units and observation
dates, foreign keys and fractional task links. SQL average tied ranks reproduce
Python gaps; task mass is conserved. Published acquisition records retain source
revisions, retrieval times and file sizes. A public-source manifest guard prevents
rebuilding AIOE aggregate evidence from the synthetic fixture.

**Local verification:** 97 unit checks, lint and compilation passed; the maintained
500-scenario audit passed. The browser calculator was compared with Python across
low demand, high demand/fast review, the quality threshold, long recruitment delay
and insufficient training hours. No external human benchmark is claimed. The
browser's export action was exercised; local generated JSON/CSV/SQLite exports
were checked directly. Browser-managed download storage was not inspected.

Clean wheel and source-distribution installations both passed outside the source tree, without optional analysis dependencies. Each exported the actual public case and SQLite warehouse, ran the workflow counterfactual, and preserved the legacy demo/research path. The wheel also served the new homepage, market page, explorer and established scenario API successfully. Remote CI and publication results are recorded after completion.

## Remaining substantive limits

- No causal workplace effect or independent human annotation has been measured.
- Platform populations, time periods and taxonomy coverage differ; a rank gap does
  not identify an adoption opportunity or an accuracy ranking.
- The organization case assumes task divisibility, no interweek backlog, fixed
  value per accepted case and qualification after specified hours. Real queues,
  deadlines, heterogeneous workers and quality severity can change the decision.
- The public comparison intentionally uses a pinned historical Anthropic release;
  it is not presented as a current workplace adoption dashboard.

These limits are stated where the corresponding evidence or decision is shown.
