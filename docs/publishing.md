# Publishing to PyPI

AI Labor Atlas publishes to PyPI through GitHub Actions Trusted Publishing. The
workflow uses short-lived OpenID Connect credentials and does not require a
stored PyPI API token.

## One-time PyPI configuration

Until the first upload creates the project, add a pending GitHub publisher from
the PyPI account publishing page with these exact values:

- PyPI project name: `ai-labor-atlas`
- GitHub owner: `JoeDHJ`
- GitHub repository: `ai-labor-atlas`
- Workflow filename: `publish.yml`
- GitHub environment: `pypi`

The GitHub repository must also contain an environment named `pypi`. The
publish job is the only job granted `id-token: write`.

## Release procedure

1. Update the package version and release-smoke assertions.
2. Merge only after the full CI matrix, release smoke, and 500-scenario audit
   pass.
3. Create a stable GitHub release whose tag exactly matches the package version,
   for example `v0.3.2`.
4. The `publish` workflow checks out that tag, verifies that the GitHub release
   is published and non-prerelease, builds one wheel and one source
   distribution, validates their metadata, and uploads them to PyPI.
5. Confirm the new version and digital attestations on
   `https://pypi.org/project/ai-labor-atlas/`.

For an existing published GitHub release that predates the workflow, run the
workflow manually from the default branch and supply its exact tag. The same
release and metadata checks apply.

PyPI does not permit replacing an uploaded filename or version. Never enable
`skip-existing` to hide a partial release; investigate and publish a new patch
version instead.
