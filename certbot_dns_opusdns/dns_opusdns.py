"""DNS Authenticator for OpusDNS."""
import logging
from typing import Callable

from certbot import errors
from certbot.plugins import dns_common

from .opusdns_client import OpusDNSClient

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for OpusDNS.
    
    This Authenticator uses the OpusDNS API to fulfill dns-01 challenges.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using OpusDNS for DNS)."
    ttl = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add: Callable) -> None:
        super().add_parser_arguments(add, default_propagation_seconds=60)
        add("credentials", help="OpusDNS credentials INI file.")

    def more_info(self) -> str:
        return "This plugin configures a DNS TXT record to respond to a dns-01 challenge using the OpusDNS API."

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            "credentials",
            "OpusDNS credentials INI file",
            {
                "api_key": "API key for OpusDNS API (opk_...)",
            },
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_opusdns_client().add_txt_record(
            validation_name, validation, self.ttl
        )

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_opusdns_client().del_txt_record(
            validation_name, validation
        )

    def _get_opusdns_client(self) -> OpusDNSClient:
        if not self.credentials:
            raise errors.PluginError("Plugin credentials not configured")
            
        api_key = self.credentials.conf("api_key")
        api_endpoint = self.credentials.conf("api_endpoint") or "https://api.opusdns.com"
        ttl = int(self.credentials.conf("ttl") or self.ttl)
        
        return OpusDNSClient(
            api_key=api_key,
            api_endpoint=api_endpoint,
            ttl=ttl,
        )
