"""Integration tests against the OpusDNS preview1 API.

These tests run against a real OpusDNS environment and require:
  - OPUSDNS_API_KEY: Valid API key for the test environment
  - OPUSDNS_API_ENDPOINT: API endpoint (e.g. https://api.preview1.opusdns.dev)
  - TEST_ZONE_NAME: DNS zone to use (e.g. certbot-test.opusdns.dev)

Skipped automatically when environment variables are not set.
"""

import os
import secrets
import string
import time

import dns.resolver
import pytest

from certbot_dns_opusdns.opusdns_client import OpusDNSClient

API_KEY = os.environ.get("OPUSDNS_API_KEY", "")
API_ENDPOINT = os.environ.get("OPUSDNS_API_ENDPOINT", "")
TEST_ZONE = os.environ.get("TEST_ZONE_NAME", "").rstrip(".")
DNS_SERVER = os.environ.get("TEST_DNS_SERVER", "")

pytestmark = pytest.mark.skipif(
    not all([API_KEY, API_ENDPOINT, TEST_ZONE]),
    reason="Integration env vars not set (OPUSDNS_API_KEY, OPUSDNS_API_ENDPOINT, TEST_ZONE_NAME)",
)


def random_subdomain(length: int = 16) -> str:
    """Generate a random subdomain label for test isolation."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


@pytest.fixture
def client():
    """Create a real OpusDNS client with appropriate nameservers."""
    nameservers = [DNS_SERVER] if DNS_SERVER else None
    return OpusDNSClient(
        api_key=API_KEY,
        api_endpoint=API_ENDPOINT,
        ttl=120,
        propagation_nameservers=nameservers,
    )


@pytest.fixture
def record_name():
    """Generate a unique _acme-challenge record name."""
    subdomain = random_subdomain()
    return f"_acme-challenge.{subdomain}.{TEST_ZONE}"


class TestIntegration:
    """Integration tests against the real OpusDNS API."""

    def test_add_and_remove_txt_record(self, client, record_name):
        """Test full lifecycle: add TXT record, verify via DNS, remove."""
        record_content = f"integration-test-{random_subdomain(8)}"

        # Add TXT record
        client.add_txt_record(record_name, record_content, 120)

        # Verify record exists via OpusDNS nameserver
        verified = self._verify_txt_record(record_name, record_content)
        assert verified, f"TXT record {record_name} not found via DNS after creation"

        # Remove TXT record
        client.del_txt_record(record_name, record_content)

        # Verify record is gone (allow some propagation time)
        time.sleep(5)
        gone = not self._verify_txt_record(record_name, record_content)
        assert gone, f"TXT record {record_name} still present after deletion"

    def test_zone_detection(self, client):
        """Test that zone detection finds a valid zone for the test domain."""
        subdomain = random_subdomain()
        fqdn = f"{subdomain}.{TEST_ZONE}"

        zone = client._find_zone(fqdn)
        # The found zone must be a suffix of our FQDN
        assert fqdn.endswith(zone), f"Zone {zone} is not a suffix of {fqdn}"

    def test_add_record_invalid_zone(self, client):
        """Test that adding to a non-existent zone fails gracefully."""
        from certbot import errors

        with pytest.raises(errors.PluginError):
            client.add_txt_record(
                "_acme-challenge.nonexistent-zone-12345.invalid",
                "test",
                120,
            )

    @staticmethod
    def _verify_txt_record(
        record_name: str,
        expected_content: str,
        timeout: int = 30,
    ) -> bool:
        """Verify TXT record via OpusDNS nameservers."""
        if DNS_SERVER:
            ns_ip = DNS_SERVER
        else:
            try:
                answers = dns.resolver.resolve("ns1.opusdns.dev", "A")
                ns_ip = str(answers[0])
            except Exception:
                ns_ip = "8.8.8.8"

        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ns_ip]
        resolver.lifetime = 10.0

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                answers = resolver.resolve(record_name, "TXT")
                for rdata in answers:
                    txt_value = str(rdata).strip('"')
                    if txt_value == expected_content:
                        return True
            except (
                dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.resolver.NoNameservers,
                dns.resolver.LifetimeTimeout,
            ):
                pass
            time.sleep(3)

        return False
