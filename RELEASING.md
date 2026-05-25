# Releasing certbot-dns-opusdns

How to publish a new release to [PyPI](https://pypi.org/project/certbot-dns-opusdns/).

## Prerequisites (one-time setup)

### PyPI Trusted Publisher

1. Sign in to [pypi.org](https://pypi.org) with the OpusDNS account.
2. Go to **Your projects → certbot-dns-opusdns → Settings → Publishing**.
3. Add a new **GitHub** publisher:
   - Owner: `OpusDNS`
   - Repository: `certbot-dns-opusdns`
   - Workflow: `release.yml`
   - Environment: `pypi`

### GitHub Environment

Create under **Settings → Environments → pypi**:

- No secrets needed (Trusted Publisher uses OIDC)
- Optionally add deployment protection rules (e.g., required reviewers)

## Release Process

### 1. Ensure CI is green

All checks run automatically on every PR and push to `main`:

- **CI** (`ci.yml`) — ruff lint, ruff format, mypy, pytest across Python 3.10–3.14, build check

No need to run tests locally — the pipeline handles it.

### 2. Update version and changelog

```bash
# Update version in pyproject.toml and __init__.py
# Update CHANGELOG.md with release date and notes
git add -A
git commit -m "Release vX.Y.Z"
git push origin main
```

### 3. Tag the release

```bash
git checkout main
git pull origin main

# Semantic version with v prefix
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 4. Automated release pipeline

Pushing a `v*` tag triggers `.github/workflows/release.yml`:

1. ✅ Runs test suite
2. 🔨 Builds sdist + wheel
3. 📦 Publishes to PyPI via Trusted Publisher (OIDC)
4. 🚀 Creates a GitHub Release with auto-generated release notes

If tests fail, the release is blocked.

### 5. Verify

1. Check [GitHub Releases](../../releases)
2. Verify on [pypi.org/project/certbot-dns-opusdns](https://pypi.org/project/certbot-dns-opusdns/)
3. Quick smoke test:
   ```bash
   pip install certbot-dns-opusdns==1.0.0
   certbot plugins | grep opusdns
   ```

## Versioning

Follow [Semantic Versioning](https://semver.org/):

| Bump | When | Example |
|------|------|---------|
| **MAJOR** | Breaking changes (removed options, changed behavior) | v2.0.0 |
| **MINOR** | New features (backward compatible) | v1.1.0 |
| **PATCH** | Bug fixes, documentation updates | v1.0.1 |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PyPI publish fails with 403 | Verify Trusted Publisher config matches workflow file/environment name exactly |
| Tests fail on tag push | Fix the issue, delete the tag (`git push --delete origin v1.0.0`), re-tag after fix |
| Package not found on PyPI | Wait a few minutes for PyPI index to update; check release workflow logs |
| Version conflict on PyPI | PyPI doesn't allow re-uploading the same version; bump patch version |
