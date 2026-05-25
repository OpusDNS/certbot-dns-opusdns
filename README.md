# certbot-dns-opusdns

[![PyPI version](https://img.shields.io/pypi/v/certbot-dns-opusdns.svg)](https://pypi.org/project/certbot-dns-opusdns/)
[![CI](https://github.com/OpusDNS/certbot-dns-opusdns/actions/workflows/ci.yml/badge.svg)](https://github.com/OpusDNS/certbot-dns-opusdns/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/certbot-dns-opusdns.svg)](https://pypi.org/project/certbot-dns-opusdns/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

OpusDNS DNS Authenticator plugin for [Certbot](https://certbot.eff.org/).

This plugin enables automatic DNS-01 challenge verification for Let's Encrypt certificates using OpusDNS as your DNS provider.

## Features

- Automatic DNS-01 challenge record management
- DNS propagation polling (verifies records via 8.8.8.8 and 1.1.1.1)
- Retry logic for rate limits and transient errors
- Support for wildcard certificates
- Configurable API endpoint (production/sandbox)
- Best-effort cleanup (doesn't fail on cleanup errors)

## Installation

### From PyPI (recommended)

```bash
pip install certbot-dns-opusdns
```

### From source

```bash
git clone https://github.com/OpusDNS/certbot-dns-opusdns
cd certbot-dns-opusdns
pip install .
```

### Docker

```bash
docker build -t certbot-dns-opusdns .
```

## Prerequisites

1. **Python 3.10+**
2. **OpusDNS Account**: Sign up at [opusdns.com](https://opusdns.com)
3. **API Key**: Create an API key via the OpusDNS dashboard
4. **DNS Zone**: Your domain must be managed by OpusDNS

## Configuration

### Credentials File

Create a credentials file (e.g., `~/.secrets/certbot/opusdns.ini`):

```ini
# Required: Your OpusDNS API key
dns_opusdns_api_key = opk_xxxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_xxxxxx

# Optional: API endpoint (defaults to https://api.opusdns.com)
# dns_opusdns_api_endpoint = https://api.opusdns.com

# Optional: TTL for TXT records in seconds (defaults to 60)
# dns_opusdns_ttl = 60
```

**Important**: Protect your credentials file:
```bash
mkdir -p ~/.secrets/certbot
chmod 700 ~/.secrets/certbot
chmod 600 ~/.secrets/certbot/opusdns.ini
```

## Usage

### Basic Certificate (Single Domain)

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  --dns-opusdns-propagation-seconds 60 \
  -d example.com
```

### Wildcard Certificate

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  --dns-opusdns-propagation-seconds 60 \
  -d example.com \
  -d "*.example.com"
```

### Multiple Domains

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  -d example.com \
  -d www.example.com \
  -d api.example.com
```

### Sandbox/Testing Environment

For testing with OpusDNS sandbox:

```ini
# opusdns.ini
dns_opusdns_api_key = opk_sandbox_key_here
dns_opusdns_api_endpoint = https://sandbox.opusdns.com
```

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials opusdns.ini \
  --server https://acme-staging-v02.api.letsencrypt.org/directory \
  -d example.com
```

## Docker Usage

### Using docker-compose

1. Copy example files:
   ```bash
   cp .env.example .env
   cp opusdns.ini.example credentials/opusdns.ini
   ```

2. Edit `.env` and `credentials/opusdns.ini` with your values

3. Run certbot:
   ```bash
   docker-compose up certbot
   ```

### Manual Docker

```bash
docker run -it --rm \
  -v $(pwd)/letsencrypt:/etc/letsencrypt \
  -v $(pwd)/credentials:/credentials:ro \
  certbot-dns-opusdns \
  certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials /credentials/opusdns.ini \
  -d example.com
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dns-opusdns-credentials` | Path to credentials INI file | Required |
| `--dns-opusdns-propagation-seconds` | Time to wait for DNS propagation | 60 |

## How It Works

1. **Zone Detection**: Iterates through domain parts to find the matching OpusDNS zone via `GET /v1/dns/{candidate}`
2. **Record Creation**: Creates `_acme-challenge` TXT record via `PATCH /v1/dns/{zone}/records` (upsert operation)
3. **DNS Propagation Polling**: Polls public DNS resolvers (8.8.8.8, 1.1.1.1) to verify record propagation
4. **Validation**: Let's Encrypt validates the challenge
5. **Cleanup**: Removes the challenge record (best-effort, logs errors)

## API Details

### Authentication
- Header: `X-Api-Key: opk_...`

### Endpoints Used
- `GET /v1/dns/{zone}` — Zone lookup for zone detection
- `PATCH /v1/dns/{zone}/records` — Create/remove TXT records

### Error Handling
- **401 Unauthorized**: Invalid API key
- **404 Not Found**: Zone doesn't exist in your account
- **429 Rate Limit**: Automatic retry with exponential backoff (max 3 attempts)
- **5xx Server Error**: Automatic retry with backoff

## Troubleshooting

### "No OpusDNS zone found for domain"
- Ensure your domain is added to OpusDNS
- Check that the zone name matches (e.g., `example.com` for `www.example.com`)

### "Invalid API key"
- Verify API key format: `opk_{26 chars}_{30 chars}_{6 chars}`
- Check API key permissions in OpusDNS dashboard
- Ensure no extra whitespace in credentials file

### "DNS propagation timeout"
- Increase `--dns-opusdns-propagation-seconds` (e.g., 120)
- Check OpusDNS dashboard for zone status
- Verify nameservers are correctly configured

### "Rate limit exceeded"
- OpusDNS has API rate limits
- Plugin automatically retries with backoff
- Reduce concurrent certificate requests

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=certbot_dns_opusdns --cov-report=html

# Lint
ruff check certbot_dns_opusdns tests

# Type check
mypy certbot_dns_opusdns
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License — See [LICENSE](LICENSE) file.

## Support

- **Issues**: [GitHub Issues](https://github.com/OpusDNS/certbot-dns-opusdns/issues)
- **Documentation**: [OpusDNS Docs](https://docs.opusdns.com)
- **Email**: support@opusdns.com
