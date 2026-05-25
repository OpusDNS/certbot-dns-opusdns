# Copilot Instructions

## Build, test, and lint

```sh
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest -v
pytest --cov=certbot_dns_opusdns --cov-report=html

# Run a single test
pytest tests/test_opusdns_client.py::TestOpusDNSClient::test_find_zone_exact_match -v

# Lint
ruff check certbot_dns_opusdns tests
ruff format --check certbot_dns_opusdns tests

# Auto-fix lint issues
ruff check --fix certbot_dns_opusdns tests
ruff format certbot_dns_opusdns tests

# Type check
mypy certbot_dns_opusdns

# Build package
python -m build
twine check dist/*
```

## Architecture

This is a Certbot DNS authenticator plugin for OpusDNS. It consists of two main files:

- **`certbot_dns_opusdns/dns_opusdns.py`** — Certbot `DNSAuthenticator` subclass
  - Registers as `dns-opusdns` plugin via entry point
  - Handles credentials setup and delegates to OpusDNSClient
- **`certbot_dns_opusdns/opusdns_client.py`** — OpusDNS API client
  - Zone discovery via `GET /v1/dns/{candidate}`
  - Record management via `PATCH /v1/dns/{zone}/records`
  - DNS propagation polling via dnspython
  - Retry logic with exponential backoff for 429/5xx

## Key conventions

### API interaction
- Authentication: `X-Api-Key` header with `opk_...` format key
- Zone detection: Iterates domain parts from most-specific to least-specific, checking each via GET
- Record ops: Uses `ops[].record` payload structure with `upsert`/`remove` operations
- Retry: Max 3 attempts with exponential backoff on 429 and 5xx responses

### Error handling
- Authentication/zone errors: Raise `certbot.errors.PluginError` immediately
- Cleanup errors: Log warnings but don't raise (best-effort)
- Network errors: Retry with backoff, then raise PluginError

### DNS propagation
- Polls 8.8.8.8 and 1.1.1.1 for TXT record after creation
- Default: 10 attempts × 6 second intervals
- Raises PluginError on timeout

### Testing
- Unit tests in `tests/` using pytest + unittest.mock
- Mock `httpx.Client` context manager for API tests
- Mock `dns.resolver.Resolver` for propagation tests
- All tests should be fast (no real network calls)

## Release process

See [RELEASING.md](../RELEASING.md) for full details. In short:
1. Update version in `pyproject.toml` and `certbot_dns_opusdns/__init__.py`
2. Update `CHANGELOG.md`
3. Tag with `v*` prefix → automated PyPI publish + GitHub Release
