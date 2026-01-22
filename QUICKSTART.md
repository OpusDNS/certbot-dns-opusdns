# Quick Start Guide

Get up and running with certbot-dns-opusdns in under 5 minutes.

## Prerequisites

- Python 3.8 or higher
- OpusDNS account with at least one DNS zone
- OpusDNS API key

## Step 1: Install Plugin

```bash
pip install certbot-dns-opusdns
```

## Step 2: Create Credentials File

Create `~/.secrets/certbot/opusdns.ini`:

```bash
mkdir -p ~/.secrets/certbot
chmod 700 ~/.secrets/certbot
```

Add your credentials:

```ini
dns_opusdns_api_key = opk_xxxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_xxxxxx
```

Secure the file:

```bash
chmod 600 ~/.secrets/certbot/opusdns.ini
```

## Step 3: Obtain Certificate

### Single Domain

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  -d example.com
```

### Wildcard Domain

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  -d example.com \
  -d "*.example.com"
```

## Step 4: Verify Installation

```bash
certbot certificates
```

## Automatic Renewal

Certbot automatically renews certificates. Test renewal:

```bash
certbot renew --dry-run
```

## Testing with Staging

For testing, use Let's Encrypt staging:

```bash
certbot certonly \
  --authenticator dns-opusdns \
  --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
  --server https://acme-staging-v02.api.letsencrypt.org/directory \
  -d test.example.com
```

## Troubleshooting

### Plugin not found
```bash
certbot plugins
# Should show "dns-opusdns" in the list
```

### Permission denied
```bash
chmod 600 ~/.secrets/certbot/opusdns.ini
```

### Zone not found
Ensure your domain is added to OpusDNS and nameservers are configured.

## Next Steps

- Read the [full documentation](README.md)
- Check out [examples](examples/)
- Report issues on [GitHub](https://github.com/opusdns/certbot-dns-opusdns/issues)
