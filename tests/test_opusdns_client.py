"""Tests for OpusDNS client."""

from unittest.mock import MagicMock, Mock, patch

import dns.resolver
import httpx
import pytest
from certbot import errors

from certbot_dns_opusdns.opusdns_client import OpusDNSClient


class TestOpusDNSClient:
    """Test suite for OpusDNSClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return OpusDNSClient(
            api_key="opk_test123456789012345678901234_123456789012345678901234567890_abcdef",
            api_endpoint="https://api.example.com",
            ttl=60,
        )

    @pytest.fixture
    def mock_zone_response(self):
        """Mock single zone API response."""
        return {"dnssec_status": "disabled", "name": "example.com."}

    def test_find_zone_exact_match(self, client, mock_zone_response):
        """Test zone detection with exact match."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_zone_response

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            zone = client._find_zone("example.com")
            assert zone == "example.com"

    def test_find_zone_subdomain(self, client, mock_zone_response):
        """Test zone detection with subdomain."""
        with patch("httpx.Client") as mock_client_class:
            mock_response_404 = Mock()
            mock_response_404.status_code = 404
            mock_response_404.json.return_value = {"error": "not found"}

            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = mock_zone_response

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            # First call (_acme-challenge.example.com) → 404, second (example.com) → 200
            mock_client.get.side_effect = [mock_response_404, mock_response_200]
            mock_client_class.return_value = mock_client

            zone = client._find_zone("_acme-challenge.example.com")
            assert zone == "example.com"

    def test_find_zone_longest_match(self, client):
        """Test zone detection prefers longest (first) match."""
        with patch("httpx.Client") as mock_client_class:
            mock_response_404 = Mock()
            mock_response_404.status_code = 404
            mock_response_404.json.return_value = {"error": "not found"}

            mock_response_found = Mock()
            mock_response_found.status_code = 200
            mock_response_found.json.return_value = {
                "dnssec_status": "disabled",
                "name": "sub.example.com.",
            }

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            # First call (test.sub.example.com) → 404, second (sub.example.com) → 200
            mock_client.get.side_effect = [mock_response_404, mock_response_found]
            mock_client_class.return_value = mock_client

            zone = client._find_zone("test.sub.example.com")
            assert zone == "sub.example.com"

    def test_find_zone_not_found(self, client):
        """Test zone detection raises error when no match."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"error": "not found"}

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(errors.PluginError, match="No OpusDNS zone found"):
                client._find_zone("notfound.com")

    def test_get_relative_name(self, client):
        """Test relative name extraction."""
        assert (
            client._get_relative_name("_acme-challenge.example.com", "example.com")
            == "_acme-challenge"
        )
        assert client._get_relative_name("example.com", "example.com") == "@"
        assert client._get_relative_name("sub.example.com", "example.com") == "sub"

    def test_get_relative_name_invalid(self, client):
        """Test relative name extraction with invalid FQDN."""
        with pytest.raises(errors.PluginError, match="not within zone"):
            client._get_relative_name("other.com", "example.com")

    def test_patch_rrset_upsert(self, client):
        """Test upsert operation."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 204

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client

            client._patch_rrset(
                zone="example.com",
                name="_acme-challenge",
                record_type="TXT",
                operation="upsert",
                ttl=60,
                rdata='"test-value"',
            )

            mock_client.patch.assert_called_once()
            call_args = mock_client.patch.call_args

            assert call_args[1]["json"]["ops"][0]["op"] == "upsert"
            assert call_args[1]["json"]["ops"][0]["record"]["name"] == "_acme-challenge"
            assert call_args[1]["json"]["ops"][0]["record"]["type"] == "TXT"
            assert call_args[1]["json"]["ops"][0]["record"]["ttl"] == 60
            assert call_args[1]["json"]["ops"][0]["record"]["rdata"] == '"test-value"'

    def test_patch_rrset_remove(self, client):
        """Test remove operation."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 204

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client

            client._patch_rrset(
                zone="example.com",
                name="_acme-challenge",
                record_type="TXT",
                operation="remove",
                ttl=60,
                rdata='"test-value"',
            )

            mock_client.patch.assert_called_once()
            call_args = mock_client.patch.call_args

            assert call_args[1]["json"]["ops"][0]["op"] == "remove"
            assert call_args[1]["json"]["ops"][0]["record"]["name"] == "_acme-challenge"
            assert call_args[1]["json"]["ops"][0]["record"]["type"] == "TXT"

    def test_patch_rrset_auth_error(self, client):
        """Test authentication error handling."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response
            )

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(errors.PluginError, match="Invalid API key"):
                client._patch_rrset(
                    zone="example.com",
                    name="_acme-challenge",
                    record_type="TXT",
                    operation="upsert",
                    ttl=60,
                    rdata='"test"',
                )

    def test_patch_rrset_zone_not_found(self, client):
        """Test zone not found error."""
        with patch("httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(errors.PluginError, match="Zone .* not found"):
                client._patch_rrset(
                    zone="example.com",
                    name="_acme-challenge",
                    record_type="TXT",
                    operation="upsert",
                    ttl=60,
                    rdata='"test"',
                )

    def test_patch_rrset_rate_limit_retry(self, client):
        """Test rate limit retry logic."""
        with patch("httpx.Client") as mock_client_class, patch("time.sleep"):
            mock_response_429 = Mock()
            mock_response_429.status_code = 429

            mock_response_204 = Mock()
            mock_response_204.status_code = 204

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.patch.side_effect = [mock_response_429, mock_response_204]
            mock_client_class.return_value = mock_client

            client._patch_rrset(
                zone="example.com",
                name="_acme-challenge",
                record_type="TXT",
                operation="upsert",
                ttl=60,
                rdata='"test"',
            )

            assert mock_client.patch.call_count == 2

    def test_wait_for_propagation_success(self, client):
        """Test DNS propagation polling succeeds."""
        mock_rdata = Mock()
        mock_rdata.__str__ = Mock(return_value='"test-value"')

        with patch("dns.resolver.Resolver") as mock_resolver_class:
            mock_resolver = Mock()
            mock_resolver.resolve.return_value = [mock_rdata]
            mock_resolver_class.return_value = mock_resolver

            client._wait_for_propagation("_acme-challenge.example.com", "test-value")

    def test_wait_for_propagation_timeout(self, client):
        """Test DNS propagation timeout."""
        client.max_attempts = 2
        client.polling_interval = 0.1

        with patch("dns.resolver.Resolver") as mock_resolver_class, patch("time.sleep"):
            mock_resolver = Mock()
            mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()
            mock_resolver_class.return_value = mock_resolver

            with pytest.raises(errors.PluginError, match="DNS propagation timeout"):
                client._wait_for_propagation("_acme-challenge.example.com", "test-value")

    def test_add_txt_record(self, client, mock_zone_response):
        """Test adding TXT record end-to-end."""
        with (
            patch("httpx.Client") as mock_client_class,
            patch.object(client, "_wait_for_propagation"),
        ):
            mock_zones_resp = Mock()
            mock_zones_resp.status_code = 200
            mock_zones_resp.json.return_value = mock_zone_response

            mock_patch_resp = Mock()
            mock_patch_resp.status_code = 204

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_zones_resp
            mock_client.patch.return_value = mock_patch_resp
            mock_client_class.return_value = mock_client

            client.add_txt_record("_acme-challenge.example.com", "test-value", 60)

            assert mock_client.patch.called

    def test_del_txt_record_best_effort(self, client, mock_zone_response):
        """Test deleting TXT record doesn't raise on error."""
        with patch("httpx.Client") as mock_client_class:
            mock_zones_resp = Mock()
            mock_zones_resp.status_code = 200
            mock_zones_resp.json.return_value = mock_zone_response

            mock_patch_resp = Mock()
            mock_patch_resp.status_code = 500
            mock_patch_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=Mock(), response=mock_patch_resp
            )

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_zones_resp
            mock_client.patch.return_value = mock_patch_resp
            mock_client_class.return_value = mock_client

            # Should not raise
            client.del_txt_record("_acme-challenge.example.com", "test-value")
