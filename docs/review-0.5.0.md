# Independent review and verification — 0.5.0

Date: 2026-11-16. Two independent read-only review agents examined the final
implementation. Both covered requirement completeness, logic, edge cases, code
quality, tests and actual runtime; one emphasized measurement, the other product
delivery. They did not edit the repository or the user's `output/` directory.

## Findings and closure

| Finding | Fix | Focused verification |
| --- | --- | --- |
| P1: mutable BLS projection URL could silently fetch a 2025–2035 workbook under a 2024–2034 label | Pin the official `2024-34.zip` archive linked by BLS's archive page; accept nested `occupation.xlsx`; validate 2024/2034 headers before replacing an existing source | A 2024 nested workbook parses; a 2025 payload is rejected and the prior destination stays intact. Both reviewers accepted the correction. |
| P1/P2: occupation snapshot used a hardcoded acquisition date, including in demo | Read build/download provenance; unknown acquisition dates are null with local modification time supplied separately; demo has synthetic source and null observed period | Explicit provenance changes the exported date; unknown/demo dates stay null. |
| P2: extremely large integer scenario input could disconnect HTTP | Convert numeric overflow into validated input failure | Unit check plus restarted server: `workforce=10**400` returns HTTP400; default scenario returns HTTP200 and 129593.75 hours. |
| P2: permissive numeric cleaning could corrupt imported market cells | Strict numeric, identity, schema, period, unit and status validation | `1e3` becomes 1000; `20garbage`, nonfinite values and wrong metadata fail. |
| P2: zero market baseline caused brief formatting failure and invalid chart indexing | Undefined percent change displays as unavailable; index chart explicitly handles a zero baseline | Brief regression check and UI source guard verified. |
| P2: demo display bounds were absent | Supply actual synthetic reference bounds and label the reference vintage | Offline research reports no undefined bounds. |
| P2: research-unavailable fallback left stale download files | Remove the seven known generated research exports before serving the notice; preserve the original explorer/API | Reviewer simulated failed research generation and verified stale exports removed. |
| UI: edited/overlapping scenario requests could leave stale output | Invalidate outputs on input edits and guard response order | Browser invalid/valid workflow checked; input changes disable the export until rerun. |

Both reviewers' focused rechecks report no unresolved P0/P1 or material scope gap.

## Independent measurement evidence

The measurement reviewer independently reproduced all four exposure wage
quartiles and the 1.936894 high/low ratio, all six common-period market changes,
the fixed raw/display relationship (rounding error below 5×10⁻⁷), manufacturing
skill coverage 85.7904% and bundle share 30.9858%, and professional/business
services coverage 91.1817% and bundle share 50.4704%.

## Runtime and interface evidence

- 84 unit tests pass; lint and compilation checks pass. The established
  500-case audit passes with zero failures. CI repeats the required checks across
  Python 3.10–3.14 and installed-distribution smoke workflows.
  All seven jobs passed in [the implementation PR run](https://github.com/JoeDHJ/ai-labor-atlas/actions/runs/43824926130).
- Clean wheel and source-distribution installations run outside the source tree:
  offline build, research, occupation search and scenario file export succeed.
  Packaged public data have 346 monthly observations and 2,007 staffing rows.
- The full public-source build regenerates 1,016 O*NET records, 18,796 tasks,
  809 exposure matches, 691 complete research SOCs and 175 skill comparison rows.
- Chrome checks cover root navigation, comparison controls, exact industry
  profile selection, task search, original explorer, Career bridge, scenario
  validation and capacity output. Desktop at 1440 pixels and mobile at 390 pixels
  show no page-level horizontal overflow. Wide tables have local scroll regions.
- Static JSON/CSV/Markdown exports return HTTP200 and parse. The scenario export
  button was exercised; the automation's browser download-completion event did
  not return, so no claim is made about a Chrome filesystem write. The equivalent
  CLI JSON file export and model payload were verified directly.
- Current screenshots were captured from the actual public build, with complete
  section boundaries and margins; the screenshot viewport was reset afterward.

## Source access limits

Direct BLS OEWS and historical-archive ZIP requests returned HTTP403 in this
environment. The archived URL was verified through the official BLS archive
page; its adapter and pre-replacement validation were tested with workbooks.
No new online archive download is claimed. The actual occupational case uses
the preserved official local acquisition from July 2026. Newly retrieved FRED
monthly observations and four BLS industry matrix pages were used for Case 2.
No private records or unverified replacement data were introduced.
