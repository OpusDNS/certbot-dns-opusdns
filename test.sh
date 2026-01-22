#!/bin/bash
# Quick test script for local development

set -e

echo "==> Installing plugin in development mode..."
pip install -e ".[dev]" > /dev/null

echo "==> Running unit tests..."
pytest -v

echo "==> Running linter..."
ruff check certbot_dns_opusdns tests || true

echo "==> Checking types..."
mypy certbot_dns_opusdns || true

echo ""
echo "==> All checks complete!"
echo ""
echo "To test with real API:"
echo "  1. Create credentials/opusdns.ini with your API key"
echo "  2. Run:"
echo "     certbot certonly --authenticator dns-opusdns \\"
echo "       --dns-opusdns-credentials credentials/opusdns.ini \\"
echo "       --server https://acme-staging-v02.api.letsencrypt.org/directory \\"
echo "       -d test.yourdomain.com"
