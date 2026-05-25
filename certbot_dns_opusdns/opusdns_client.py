"""OpusDNS API client for DNS operations."""

import logging
import time

import dns.resolver
import httpx
from certbot import errors

logger = logging.getLogger(__name__)


class OpusDNSClient:
    """Client for interacting with the OpusDNS API."""

    def __init__(
        self,
        api_key: str,
        api_endpoint: str = "https://api.opusdns.com",
        ttl: int = 60,
    ):
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.ttl = ttl
        self.max_attempts = 10
        self.polling_interval = 6

    def add_txt_record(self, record_name: str, record_content: str, ttl: int) -> None:
        """Add a TXT record.

        Args:
            record_name: Full DNS name (e.g., _acme-challenge.example.com)
            record_content: TXT record content
            ttl: TTL in seconds

        Raises:
            errors.PluginError: If API call fails
        """
        zone = self._find_zone(record_name)
        relative_name = self._get_relative_name(record_name, zone)

        logger.info(f"Adding TXT record {relative_name} to zone {zone}")

        try:
            self._patch_rrset(
                zone=zone,
                name=relative_name,
                record_type="TXT",
                ttl=ttl,
                rdata=f'"{record_content}"',
                operation="upsert",
            )
        except Exception as e:
            raise errors.PluginError(f"Failed to add TXT record: {e}") from e

        self._wait_for_propagation(record_name, record_content)

    def del_txt_record(self, record_name: str, record_content: str) -> None:
        """Remove a TXT record (best-effort).

        Args:
            record_name: Full DNS name
            record_content: TXT record content

        Note:
            Errors during cleanup are logged but not raised.
        """
        try:
            zone = self._find_zone(record_name)
            relative_name = self._get_relative_name(record_name, zone)

            logger.info(f"Removing TXT record {relative_name} from zone {zone}")

            self._patch_rrset(
                zone=zone,
                name=relative_name,
                record_type="TXT",
                ttl=self.ttl,
                rdata=f'"{record_content}"',
                operation="remove",
            )
        except Exception as e:
            logger.warning(f"Failed to remove TXT record (non-fatal): {e}")

    def _wait_for_propagation(self, record_name: str, record_content: str) -> None:
        """Poll public DNS resolvers to verify TXT record propagation.

        Args:
            record_name: Full DNS name to check
            record_content: Expected TXT record content

        Raises:
            errors.PluginError: If record is not found after max attempts
        """
        resolvers = ["8.8.8.8", "1.1.1.1"]

        for attempt in range(self.max_attempts):
            for resolver_ip in resolvers:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [resolver_ip]
                    resolver.lifetime = 10.0

                    answers = resolver.resolve(record_name, "TXT")
                    for rdata in answers:
                        txt_value = str(rdata).strip('"')
                        if txt_value == record_content:
                            logger.debug(
                                f"TXT record verified via {resolver_ip} (attempt {attempt + 1})"
                            )
                            return
                except (
                    dns.resolver.NXDOMAIN,
                    dns.resolver.NoAnswer,
                    dns.resolver.NoNameservers,
                    dns.resolver.LifetimeTimeout,
                    Exception,
                ) as e:
                    logger.debug(f"DNS check attempt {attempt + 1} via {resolver_ip}: {e}")

            if attempt < self.max_attempts - 1:
                time.sleep(self.polling_interval)

        raise errors.PluginError(
            f"DNS propagation timeout: TXT record for {record_name} "
            f"not found after {self.max_attempts} attempts"
        )

    def _find_zone(self, fqdn: str) -> str:
        """Find the OpusDNS zone for a given FQDN by checking the API.

        Iterates through domain parts until a valid zone is found.

        Args:
            fqdn: Fully qualified domain name

        Returns:
            Zone name (e.g., "example.com")

        Raises:
            errors.PluginError: If no matching zone found
        """
        # Normalize FQDN (remove trailing dot if present)
        fqdn = fqdn.rstrip(".")
        parts = fqdn.split(".")

        # Try progressively shorter domain names starting from the full FQDN
        for i in range(0, len(parts) - 1):
            candidate = ".".join(parts[i:])
            logger.debug(f"Trying zone: {candidate}")

            try:
                with httpx.Client() as client:
                    response = client.get(
                        f"{self.api_endpoint}/v1/dns/{candidate}",
                        headers={"X-Api-Key": self.api_key},
                        timeout=30.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # Valid zone response contains dnssec_status
                        if "dnssec_status" in data:
                            logger.debug(f"Found zone: {candidate}")
                            return candidate

            except httpx.RequestError as e:
                logger.debug(f"Request error checking zone {candidate}: {e}")

        raise errors.PluginError(f"No OpusDNS zone found for {fqdn}")

    def _get_relative_name(self, fqdn: str, zone: str) -> str:
        """Get relative record name within a zone.

        Args:
            fqdn: Fully qualified domain name
            zone: Zone name

        Returns:
            Relative name (e.g., "_acme-challenge" for
            _acme-challenge.example.com in zone example.com)
        """
        fqdn = fqdn.rstrip(".")
        zone = zone.rstrip(".")

        if fqdn == zone:
            return "@"

        if fqdn.endswith(f".{zone}"):
            return fqdn[: -(len(zone) + 1)]

        raise errors.PluginError(f"FQDN {fqdn} is not within zone {zone}")

    def _patch_rrset(
        self,
        zone: str,
        name: str,
        record_type: str,
        operation: str,
        ttl: int | None = None,
        rdata: str | None = None,
    ) -> None:
        """Patch a DNS record set via OpusDNS API with retry logic.

        Args:
            zone: Zone name
            name: Relative record name
            record_type: Record type (e.g., "TXT")
            operation: "upsert" or "remove"
            ttl: TTL in seconds (required for both upsert and remove)
            rdata: Record data (required for both upsert and remove)

        Raises:
            errors.PluginError: If API call fails after retries
        """
        record: dict[str, str | int] = {
            "name": name,
            "type": record_type,
        }
        if ttl is not None:
            record["ttl"] = ttl
        if rdata is not None:
            record["rdata"] = rdata

        payload = {
            "ops": [
                {
                    "op": operation,
                    "record": record,
                }
            ]
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client() as client:
                    response = client.patch(
                        f"{self.api_endpoint}/v1/dns/{zone}/records",
                        headers={
                            "X-Api-Key": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=30.0,
                    )

                    if response.status_code == 401:
                        raise errors.PluginError("Invalid API key")

                    if response.status_code == 404:
                        raise errors.PluginError(f"Zone {zone} not found")

                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            wait_time = 2**attempt
                            logger.warning(f"Rate limited, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        raise errors.PluginError("Rate limit exceeded")

                    if response.status_code >= 500 and attempt < max_retries - 1:
                        wait_time = 2**attempt
                        logger.warning(f"Server error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return

            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    error_msg = f"HTTP {e.response.status_code}"
                    try:
                        error_data = e.response.json()
                        if "message" in error_data:
                            error_msg = error_data["message"]
                    except Exception:
                        pass
                    raise errors.PluginError(f"API request failed: {error_msg}") from e
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise errors.PluginError(f"Network error: {e}") from e
                wait_time = 2**attempt
                logger.warning(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)
