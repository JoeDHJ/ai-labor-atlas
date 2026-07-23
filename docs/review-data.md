# Worker review context

AI Labor Atlas can display public worker comments alongside an occupation's structured labor-market evidence. This layer is intentionally contextual. It does not create an occupation rating, estimate sentiment, or change `ai_exposure`, wages, employment, projections, or Career Fit scores.

## Public import contract

Place an optional local file at `data/processed/reviews.json`. The file may be a JSON list or an object with a `reviews` list. Each public row must contain:

```json
{
  "review_id": "stable-source-id",
  "onet_soc_code": "15-2051.00",
  "source": "user_submitted | reddit | indeed | other",
  "source_url": "https://example.com/source",
  "review_scope": "occupation | employer_role | job_posting",
  "review_date": "2025-04-03",
  "topics": ["pay_benefits", "interview_management", "work_environment"],
  "rating": 3,
  "excerpt": "A short, attributable excerpt for public display."
}
```

`source_url`, `review_date`, `rating`, employer, job title, location, and author display name are optional. `rating` is shown only as supplied; it is never averaged. The importer uses a public-field allowlist so private contact details and importer-only notes do not reach the dashboard.

The dashboard keeps comments from different sources and scopes visible together. A positive, negative, or mixed experience may be useful to a job seeker, but no comment is treated as a verified fact or as representative of all workers. Source, date, scope, and link remain attached wherever available.

When more than one comment is available, the dashboard lets readers filter by source and topic. The filtered count is shown against the total count, and any display cap is stated, so a narrow view cannot be mistaken for the full set. When a source requires attribution, an imported display name is shown when supplied.

## Validate before publishing

Run the release check before copying an import into the processed data directory:

```powershell
python -m ai_labor_atlas.cli validate-reviews --input path\to\reviews.json
```

The command prints a JSON report with `valid`, row counts, duplicate IDs, occupation coverage, source counts, topic counts, and actionable row numbers. It does not print review excerpts. Exit code `0` means the strict dashboard loader can accept the complete file; exit code `2` means the file must be corrected first. A missing default import is reported as an empty optional layer rather than an error.

## Source and rights boundary

Do not scrape or redistribute platform content by default. Before importing Reddit, Indeed, or another platform, confirm the current platform terms, API terms, attribution requirements, user-content rights, privacy obligations, and any applicable license. Keep a source registry entry and a reproducible import record outside the public excerpt when the platform requires it. User-submitted comments should have clear consent for public display.

The product's disclosure is intentionally unobtrusive but always available through **About these reviews**. It states that comments may be incomplete, subjective, outdated, or biased and are not representative of all workers.

If the import file is malformed, contains duplicate IDs, or uses an invalid O*NET code, the dashboard refuses to start and reports the import error. This prevents a partial or ambiguous review layer from appearing as if it were complete.

## Connection to Career Fit

Career Fit remains job-posting-level: it scores the supplied posting against the supplied candidate evidence. The optional connection first suggests standard occupations from title evidence, then requires the user to confirm one. Only after confirmation does it request the matching Atlas occupation context. Worker comments are shown as a separate reading layer and cannot change job-specific fit, readiness, or eligibility signals.
