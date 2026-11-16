Current release: **0.6.1**. The new research workbench and its three-round review are documented in [review-0.6.0.md](review-0.6.0.md). The record below preserves the completed 0.5.0 work.



# Labor Intelligence 0.5.0 implementation record



Owner: Haojian Dui. Started: 2026-11-16. Branch: `codex/labor-intelligence-0.5.0`.



## Preserve



Package/CLI, source registry, official occupation crosswalk, 0–100 AIOE display,

occupation explorer, task explorer, Career bridge, optional consent-based semantic

review, worker-context validation. Preserve the pre-existing untracked `output/`.



## Change



Replace automatic file hashing with version/date/size/schema provenance. Retain

signed source AIOE beside its fixed display transform. Reproduce coverage using

one record per O*NET occupation. Correct obsolete version headings and distinguish

OEWS observation dates from the legacy `employment_2024` API field.



## Add and acceptance path



1. Executable time-series manifest and public BLS/FRED monthly labor demand,

   employment and wage observations; occupational skill composition and snapshots.

2. Two connected reproducible public-data cases, inspectable exhibits and reports.

3. Explicit task/adoption/training scenario model with sensitivity and strict input

   validation; no conversion of exposure into job-loss probabilities.

4. Research dashboard, structured downloads, Markdown brief, portfolio.v1 adapter,

   deterministic offline workflow and real-source update workflow.

5. Official employer requirement matrix, clean wheel/sdist installation, browser

   checks, independent read-only review, fixes, CI, commit and immutable release.



## Initial inspection



- Source and remote 0.4.0 agree; initial branch has no tracked user changes.

- New task brief and pre-existing `output/` are the only untracked paths.

- Public raw sources already present from July 2026. They will keep their local

  provenance; newly fetched monthly data will carry today's retrieval date.

- README reported 79.0% exposure coverage; reproduction found 809/1,016 = 79.625984%, corrected to 79.6%.

- Direct BLS historical ZIP endpoint returned HTTP 403. FRED public CSV transport

  works; no authenticated data or private records are required.

- AIOE upstream has a citation instruction but no explicit redistribution license

  visible in its root. Do not bundle its occupation-level raw/derived values in

  the package; generate locally from the public source. Aggregate case exhibits

  and a clearly labeled synthetic offline fixture can be distributed.



## Verification and release



Implemented the complete requested research path. Actual results: 691 complete

unique SOCs; high/low exposure wage ratio 1.936894; 346 monthly observations;

2,007 BLS staffing rows; 175 skill profile rows across three occupation families

and two industries. The default scenario yields 129593.75 year-3 net annual

capacity hours, conditional on its displayed assumptions.



84 unit tests, lint and compilation pass; the maintained 500-case audit passes.

Real-source analysis and selected report figures were regenerated. Clean wheel

and sdist workflows run in separate environments outside the source tree.

Desktop/mobile browser checks and current screenshots are complete.



Two read-only reviewers covered all six required dimensions and verified the

fixes. No unresolved P0/P1 or material scope gap remains; details and actual

source-access limits are in `docs/review-0.5.0.md`.



Implementation commit: `cc72725`; reviewable [PR #11](https://github.com/JoeDHJ/ai-labor-atlas/pull/11).

Both [branch CI](https://github.com/JoeDHJ/ai-labor-atlas/actions/runs/43824902557)

and [PR CI](https://github.com/JoeDHJ/ai-labor-atlas/actions/runs/43824926130)

passed all seven jobs: Python 3.10–3.14, the 500-case audit and clean-distribution

release smoke. Subsequent changes to this record contain release metadata only.



Public release entry points:

[GitHub v0.5.0](https://github.com/JoeDHJ/ai-labor-atlas/releases/tag/v0.5.0),

[PyPI 0.5.0](https://pypi.org/project/ai-labor-atlas/0.5.0/).

The GitHub release and its publish workflow provide the final publication status.

The local worktree keeps the user's original untracked `output/` unchanged.

