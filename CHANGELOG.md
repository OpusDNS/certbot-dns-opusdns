# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-01-XX

### Added
- Initial release
- DNS-01 challenge authentication for Certbot
- OpusDNS API client with httpx
- Automatic zone detection from FQDN
- DNS propagation polling with dnspython
- Retry logic for rate limits (429) and server errors (5xx)
- Support for wildcard certificates
- Configurable API endpoint (production/sandbox)
- Best-effort cleanup (logs errors instead of failing)
- Comprehensive unit tests with pytest
- Docker support with Dockerfile and docker-compose.yml
- GitHub Actions CI/CD pipeline
- PyPI packaging configuration

### Features
- TTL configuration (default: 60 seconds)
- Propagation timeout configuration (default: 60 seconds)
- Credentials file support (opusdns.ini)
- Multiple DNS resolver polling (8.8.8.8, 1.1.1.1)
- Zone caching to minimize API calls
- Exponential backoff for retries

### Documentation
- Comprehensive README with examples
- API reference documentation
- Contributing guide
- Docker usage examples
- Troubleshooting guide

[Unreleased]: https://github.com/opusdns/certbot-dns-opusdns/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/opusdns/certbot-dns-opusdns/releases/tag/v1.0.0
