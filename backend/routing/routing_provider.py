"""
Routing provider abstraction layer.
Provides a pluggable interface for road network routing providers (OSRM, commercial truck APIs).
"""
import abc
import logging
import math
import time
import requests
from typing import List, Dict, Any, Optional

from .exceptions import (
    RouteNotFoundError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    MalformedProviderResponseError,
    ProviderNetworkError,
)

logger = logging.getLogger('spotter.routing')

DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; SpotterWeatherRouting/2.0; +https://github.com/faizanali2k05/spotter-weather-routing)'
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 2
INITIAL_BACKOFF_SECONDS = 0.5


class RoutingProvider(abc.ABC):
    """Abstract base class for geospatial routing providers."""

    @abc.abstractmethod
    def get_routes(self, origin: Dict[str, Any], destination: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Request up to three distinct route alternatives between origin and destination.
        Returns a list of dictionaries with:
          - distance_meters: float
          - duration_seconds: float
          - geometry: List[List[float]] (GeoJSON [lon, lat] coordinates)
        """
        pass

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Name of the routing provider."""
        pass

    @property
    @abc.abstractmethod
    def is_truck_specific(self) -> bool:
        """Indicates if the provider enforces commercial truck restrictions (height, weight, hazmat)."""
        pass


def deduplicate_routes(routes: List[Dict[str, Any]], tolerance_ratio: float = 0.015) -> List[Dict[str, Any]]:
    """
    Remove duplicate or near-identical routes returned by routing engines.
    Two routes are considered duplicates if their distance and duration are within tolerance_ratio (e.g., 1.5%)
    and their sample geometry points heavily overlap.
    """
    if len(routes) <= 1:
        return routes

    unique_routes: List[Dict[str, Any]] = []
    for candidate in routes:
        c_dist = candidate.get('distance', 0)
        c_dur = candidate.get('duration', 0)
        c_coords = candidate.get('geometry', {}).get('coordinates', [])

        is_dup = False
        for kept in unique_routes:
            k_dist = kept.get('distance', 0)
            k_dur = kept.get('duration', 0)
            k_coords = kept.get('geometry', {}).get('coordinates', [])

            # Check distance & duration similarity
            dist_diff = abs(c_dist - k_dist) / max(1.0, k_dist)
            dur_diff = abs(c_dur - k_dur) / max(1.0, k_dur)

            if dist_diff < tolerance_ratio and dur_diff < tolerance_ratio:
                # Also check midpoint coordinate proximity
                if c_coords and k_coords:
                    c_mid = c_coords[len(c_coords) // 2]
                    k_mid = k_coords[len(k_coords) // 2]
                    coord_dist = math.hypot(c_mid[0] - k_mid[0], c_mid[1] - k_mid[1])
                    if coord_dist < 0.05:  # within ~3 miles at midpoint
                        is_dup = True
                        break

        if not is_dup:
            unique_routes.append(candidate)

    return unique_routes


class OSRMProvider(RoutingProvider):
    """
    Open Source Routing Machine (OSRM) driving routing provider using the public demo endpoint.
    Notice: The OSRM public demo uses OpenStreetMap car driving profiles and does NOT enforce
    heavy vehicle bridge clearances, axle weight limits, or hazmat restrictions.
    """

    def __init__(self, base_url: str = 'https://router.project-osrm.org', session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()

    @property
    def provider_name(self) -> str:
        return 'OSRM (Open Source Routing Machine)'

    @property
    def is_truck_specific(self) -> bool:
        return False

    def get_routes(self, origin: Dict[str, Any], destination: Dict[str, Any]) -> List[Dict[str, Any]]:
        orig_lon, orig_lat = origin['lon'], origin['lat']
        dest_lon, dest_lat = destination['lon'], destination['lat']

        coords = f"{orig_lon},{orig_lat};{dest_lon},{dest_lat}"
        url = f"{self.base_url}/route/v1/driving/{coords}"
        params = {
            'alternatives': 'true',
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'false',
        }
        headers = {
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept': 'application/json',
        }

        last_exception = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
                if resp.status_code == 429:
                    raise ProviderRateLimitError("OSRM public demo API rate limit exceeded.")
                if resp.status_code >= 500:
                    raise ProviderNetworkError(f"OSRM server error HTTP {resp.status_code}.")
                resp.raise_for_status()

                try:
                    payload = resp.json()
                except ValueError as json_err:
                    raise MalformedProviderResponseError("Failed to decode OSRM JSON response.") from json_err

                raw_routes = payload.get('routes', [])
                if not raw_routes:
                    code = payload.get('code')
                    if code == 'NoRoute':
                        raise RouteNotFoundError(f"No drivable route found between {origin.get('name')} and {destination.get('name')}.")
                    raise RouteNotFoundError("No drivable route found for the given coordinates.")

                deduped = deduplicate_routes(raw_routes)
                # Keep up to 3 distinct alternatives; never fabricate routes
                selected = deduped[:3]

                formatted = []
                for r in selected:
                    coords = r.get('geometry', {}).get('coordinates', [])
                    if not coords or len(coords) < 2:
                        continue
                    formatted.append({
                        'distance_meters': float(r['distance']),
                        'duration_seconds': float(r['duration']),
                        'geometry': coords,
                    })

                if not formatted:
                    raise RouteNotFoundError("OSRM returned routes with invalid or empty geometry.")

                return formatted

            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as exc:
                last_exception = ProviderTimeoutError(f"OSRM routing request timed out after {REQUEST_TIMEOUT_SECONDS}s.")
            except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as exc:
                last_exception = ProviderNetworkError(f"Network error communicating with OSRM: {str(exc)}")
            except (RouteNotFoundError, ProviderRateLimitError, MalformedProviderResponseError):
                raise
            except Exception as exc:
                last_exception = ProviderNetworkError(f"Unexpected error calling OSRM: {str(exc)}")

            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_BACKOFF_SECONDS * (2 ** attempt))

        if last_exception:
            raise last_exception
        raise RouteNotFoundError("Unable to retrieve routes from OSRM.")


class CommercialTruckRoutingProviderAdapter(RoutingProvider):
    """
    Adapter demonstrating commercial truck-specific routing provider integration
    (e.g., Here Fleet Telematics, Mapbox Directions Truck profile, or TomTom Truck).
    
    Commercial truck routing requires:
      - Vehicle gross weight (load + tare)
      - Axle count & max weight per axle
      - Vehicle height, width, and length
      - Hazardous materials (hazmat) classifications
      - Tunnel restrictions and commercial truck exclusions
    """

    def __init__(self, api_key: Optional[str] = None, fallback_provider: Optional[RoutingProvider] = None):
        self.api_key = api_key
        self.fallback = fallback_provider or OSRMProvider()

    @property
    def provider_name(self) -> str:
        return 'Commercial Truck Routing Adapter (HERE / Mapbox Enterprise)'

    @property
    def is_truck_specific(self) -> bool:
        return bool(self.api_key)

    def get_routes(self, origin: Dict[str, Any], destination: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.api_key:
            logger.info("Commercial truck API key not configured; falling back to OSRM with advisory warning.")
            return self.fallback.get_routes(origin, destination)

        # Enterprise truck endpoint integration stub:
        # Calls the commercial provider endpoint with truck dimensions and credentials.
        raise NotImplementedError("Commercial truck provider requires an active enterprise API key and license.")


def get_routing_provider(provider_type: Optional[str] = None) -> RoutingProvider:
    """Factory function for acquiring the configured routing provider."""
    # Default to OSRM free provider
    return OSRMProvider()

