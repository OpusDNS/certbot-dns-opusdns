# certbot-dns-opusdns

OpusDNS DNS Authenticator plugin for [Certbot](https://certbot.eff.org/).

This plugin enables automatic DNS-01 challenge verification for Let's Encrypt certificates using OpusDNS as your DNS provider.

## Features

- Automatic DNS-01 challenge record management
- DNS propagation polling (ensures records are live before validation)
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
git clone https://github.com/opusdns/certbot-dns-opusdns
cd certbot-dns-opusdns
pip install .
```

### Docker

```bash
docker build -t certbot-dns-opusdns .
```

## Prerequisites

1. **OpusDNS Account**: Sign up at [opusdns.com](https://opusdns.com)
2. **API Key**: Create an API key via the OpusDNS dashboard or API:
   ```bash
   curl -X POST https://api.opusdns.com/auth/client_credentials \
     -H "Authorization: Bearer <your_user_token>" \
     -H "Content-Type: application/json"
   ```
3. **DNS Zone**: Your domain must be managed by OpusDNS

## Configuration

### Credentials File

Create a credentials file (e.g., `opusdns.ini`):

```ini
# Required: Your OpusDNS API key
dns_opusdns_api_key = opk_xxxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_xxxxxx

# Optional: API endpoint (defaults to https://api.opusdns.com)
dns_opusdns_api_endpoint = https://api.opusdns.com

# Optional: TTL for TXT records in seconds (defaults to 60)
dns_opusdns_ttl = 60
```

**Important**: Protect your credentials file:
```bash
chmod 600 opusdns.ini
```

## Usage

### Basic Certificate (Single Domain)

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials /path/to/opusdns.ini \
  --dns-opusdns-propagation-seconds 60 \
  -d example.com
```

### Wildcard Certificate

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials /path/to/opusdns.ini \
  --dns-opusdns-propagation-seconds 60 \
  -d example.com \
  -d "*.example.com"
```

### Multiple Domains

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials /path/to/opusdns.ini \
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

1. **Zone Detection**: Plugin lists your OpusDNS zones and finds the longest matching zone for your domain
2. **Record Creation**: Creates `_acme-challenge` TXT record via `PATCH /v1/dns/{zone}/rrsets` (upsert operation)
3. **DNS Polling**: Polls public DNS (8.8.8.8, 1.1.1.1) to verify record propagation (10 attempts × 6s)
4. **Validation**: Let's Encrypt validates the challenge
5. **Cleanup**: Removes the challenge record (best-effort, logs errors)

## API Details

### Authentication
- Header: `X-Api-Key: opk_...`
- Format: 67 characters total

### Endpoints Used
- `GET /v1/dns` - List zones for zone detection
- `PATCH /v1/dns/{zone}/rrsets` - Create/remove TXT records

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

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=certbot_dns_opusdns --cov-report=html
```

### Docker Tests

```bash
docker-compose up test
```

## License

MIT License - See [LICENSE](LICENSE) file

## Support

- **Issues**: [GitHub Issues](https://github.com/opusdns/certbot-dns-opusdns/issues)
- **Documentation**: [OpusDNS Docs](https://docs.opusdns.com)
- **Email**: support@opusdns.com
