"""Tests for DNS authenticator."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from certbot import errors
from certbot.plugins import dns_test_common

from certbot_dns_opusdns.dns_opusdns import Authenticator


class AuthenticatorTest(dns_test_common.BaseAuthenticatorTest):
    """Test suite for Authenticator."""

    def setUp(self):
        super().setUp()
        
        from certbot.plugins import dns_test_common
        
        self.config = Mock()
        self.config.verb = "certonly"
        self.config.config_dir = "/tmp/certbot"
        self.config.work_dir = "/tmp/certbot/work"
        
        self.auth = Authenticator(self.config, "dns-opusdns")

    def test_more_info(self):
        """Test more_info method."""
        assert "OpusDNS" in self.auth.more_info()

    def test_setup_credentials_missing_file(self):
        """Test credential setup with missing file."""
        self.config.dns_opusdns_credentials = None
        
        with pytest.raises(errors.PluginError):
            self.auth._setup_credentials()

    def test_perform(self):
        """Test _perform method."""
        mock_client = Mock()
        
        with patch.object(self.auth, "_get_opusdns_client", return_value=mock_client):
            self.auth._perform("example.com", "_acme-challenge.example.com", "test-validation")
            
            mock_client.add_txt_record.assert_called_once_with(
                "_acme-challenge.example.com",
                "test-validation",
                60,
            )

    def test_cleanup(self):
        """Test _cleanup method."""
        mock_client = Mock()
        
        with patch.object(self.auth, "_get_opusdns_client", return_value=mock_client):
            self.auth._cleanup("example.com", "_acme-challenge.example.com", "test-validation")
            
            mock_client.del_txt_record.assert_called_once_with(
                "_acme-challenge.example.com",
                "test-validation",
            )


if __name__ == "__main__":
    pytest.main([__file__])
