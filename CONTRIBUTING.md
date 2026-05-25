# Contributing to certbot-dns-opusdns

Thank you for considering contributing to certbot-dns-opusdns!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/OpusDNS/certbot-dns-opusdns
   cd certbot-dns-opusdns
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

```bash
pytest -v
pytest --cov=certbot_dns_opusdns --cov-report=html
```

## Code Style

We use:
- **ruff** for linting and formatting
- **mypy** for type checking
- **pytest** for testing

Run checks before committing:
```bash
ruff check certbot_dns_opusdns tests
ruff format --check certbot_dns_opusdns tests
mypy certbot_dns_opusdns
pytest -v
```

Auto-fix formatting:
```bash
ruff check --fix certbot_dns_opusdns tests
ruff format certbot_dns_opusdns tests
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add/update tests as needed
5. Ensure all checks pass (`ruff check`, `mypy`, `pytest`)
6. Update documentation if needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your fork (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Testing Against OpusDNS Sandbox

To test with real API calls:

1. Get a sandbox API key from https://sandbox.opusdns.com
2. Create `~/.secrets/certbot/opusdns.ini`:
   ```ini
   dns_opusdns_api_key = opk_sandbox_...
   dns_opusdns_api_endpoint = https://sandbox.opusdns.com
   ```
3. Run integration test:
   ```bash
   certbot certonly \
     --authenticator dns-opusdns \
     --dns-opusdns-credentials ~/.secrets/certbot/opusdns.ini \
     --server https://acme-staging-v02.api.letsencrypt.org/directory \
     -d test.yourdomain.com
   ```

## Reporting Issues

When reporting issues, please include:
- Plugin version (`pip show certbot-dns-opusdns`)
- Python version (`python --version`)
- Certbot version (`certbot --version`)
- Full command used
- Error message/traceback
- OpusDNS API environment (production/sandbox)

## Code of Conduct

Be respectful and constructive. We're all here to make great software together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
