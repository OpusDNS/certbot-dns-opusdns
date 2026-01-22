"""OpusDNS API client for DNS operations."""
import logging
import time
from typing import List, Optional

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
        polling_interval: int = 6,
        max_attempts: int = 10,
    ):
        self.api_key = api_key
        self.api_endpoint = api_endpoint.rstrip("/")
        self.ttl = ttl
        self.polling_interval = polling_interval
        self.max_attempts = max_attempts
        self._zone_cache: Optional[List[str]] = None
        
    def add_txt_record(self, record_name: str, record_content: str, ttl: int) -> None:
        """Add a TXT record and wait for DNS propagation.
        
        Args:
            record_name: Full DNS name (e.g., _acme-challenge.example.com)
            record_content: TXT record content
            ttl: TTL in seconds
            
        Raises:
            errors.PluginError: If API call fails or DNS doesn't propagate
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
            raise errors.PluginError(f"Failed to add TXT record: {e}")
        
        # Poll DNS to verify propagation
        self._wait_for_propagation(record_name, record_content)
        
    def del_txt_record(self, record_name: str, record_content: str) -> None:
        """Remove a TXT record (best-effort).
        
        Args:
            record_name: Full DNS name
            record_content: TXT record content (unused, for interface compatibility)
            
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
                operation="remove",
            )
        except Exception as e:
            logger.warning(f"Failed to remove TXT record (non-fatal): {e}")

    def _find_zone(self, fqdn: str) -> str:
        """Find the OpusDNS zone for a given FQDN.
        
        Args:
            fqdn: Fully qualified domain name
            
        Returns:
            Zone name (e.g., "example.com")
            
        Raises:
            errors.PluginError: If no matching zone found
        """
        zones = self._get_zones()
        
        # Normalize FQDN (remove trailing dot if present)
        fqdn = fqdn.rstrip(".")
        
        # Extract potential zone names from FQDN
        parts = fqdn.split(".")
        candidates = []
        for i in range(len(parts)):
            candidates.append(".".join(parts[i:]))
        
        # Match longest zone name
        for candidate in candidates:
            for zone in zones:
                zone_name = zone.rstrip(".")
                if candidate == zone_name:
                    return zone_name
        
        raise errors.PluginError(
            f"No OpusDNS zone found for {fqdn}. "
            f"Available zones: {', '.join(zones)}"
        )

    def _get_zones(self) -> List[str]:
        """List all DNS zones from OpusDNS API with caching.
        
        Returns:
            List of zone names
            
        Raises:
            errors.PluginError: If API call fails
        """
        if self._zone_cache is not None:
            return self._zone_cache
            
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_endpoint}/v1/dns",
                    headers={"X-Api-Key": self.api_key},
                    params={"page": 1, "page_size": 100},
                    timeout=30.0,
                )
                
                if response.status_code == 401:
                    raise errors.PluginError("Invalid API key")
                    
                response.raise_for_status()
                data = response.json()
                
                zones = [zone["name"] for zone in data.get("results", [])]
                self._zone_cache = zones
                return zones
                
        except httpx.HTTPStatusError as e:
            raise errors.PluginError(f"Failed to list zones: {e}")
        except Exception as e:
            raise errors.PluginError(f"Failed to communicate with OpusDNS API: {e}")

    def _get_relative_name(self, fqdn: str, zone: str) -> str:
        """Get relative record name within a zone.
        
        Args:
            fqdn: Fully qualified domain name
            zone: Zone name
            
        Returns:
            Relative name (e.g., "_acme-challenge" for _acme-challenge.example.com in zone example.com)
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
        ttl: Optional[int] = None,
        rdata: Optional[str] = None,
    ) -> None:
        """Patch a DNS record set via OpusDNS API with retry logic.
        
        Args:
            zone: Zone name
            name: Relative record name
            record_type: Record type (e.g., "TXT")
            operation: "upsert" or "remove"
            ttl: TTL in seconds (required for upsert)
            rdata: Record data (required for upsert)
            
        Raises:
            errors.PluginError: If API call fails after retries
        """
        payload = {
            "ops": [
                {
                    "op": operation,
                    "rrset": {
                        "name": name,
                        "type": record_type,
                    },
                }
            ]
        }
        
        if operation == "upsert":
            payload["ops"][0]["rrset"]["ttl"] = ttl
            payload["ops"][0]["rrset"]["records"] = [{"rdata": rdata}]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client() as client:
                    response = client.patch(
                        f"{self.api_endpoint}/v1/dns/{zone}/rrsets",
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
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limited, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        raise errors.PluginError("Rate limit exceeded")
                    
                    if response.status_code >= 500:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
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
                    raise errors.PluginError(f"API request failed: {error_msg}")
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise errors.PluginError(f"Network error: {e}")
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)

    def _wait_for_propagation(self, record_name: str, expected_value: str) -> None:
        """Poll DNS to verify TXT record propagation.
        
        Args:
            record_name: Full DNS name to query
            expected_value: Expected TXT record value (without quotes)
            
        Raises:
            errors.PluginError: If record doesn't propagate within timeout
        """
        logger.info(f"Polling DNS for {record_name} propagation...")
        
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
        
        for attempt in range(self.max_attempts):
            try:
                answers = resolver.resolve(record_name, "TXT")
                for rdata in answers:
                    # TXT records are returned with quotes
                    txt_value = str(rdata).strip('"')
                    if txt_value == expected_value:
                        logger.info(f"DNS propagation verified after {attempt + 1} attempts")
                        return
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                pass
            
            if attempt < self.max_attempts - 1:
                logger.debug(f"Record not found, attempt {attempt + 1}/{self.max_attempts}")
                time.sleep(self.polling_interval)
        
        raise errors.PluginError(
            f"DNS propagation timeout: {record_name} did not propagate within "
            f"{self.max_attempts * self.polling_interval} seconds"
        )
