"""
Geocoding service with resilient multi-provider fallback.
Primary: OpenStreetMap Nominatim
Fallback: Open-Meteo Geocoding API
"""
import logging
import time
import requests
from typing import Dict, Any, Optional

from .exceptions import LocationNotFoundError, GeocodingError, ProviderTimeoutError, ProviderRateLimitError

logger = logging.getLogger('spotter.geocoding')

DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; SpotterWeatherRouting/2.0; +https://github.com/faizanali2k05/spotter-weather-routing)'
REQUEST_TIMEOUT_SECONDS = 10

# In-memory LRU/dict cache for geocoded queries
GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}


def _geocode_nominatim(query: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Geocode query via OpenStreetMap Nominatim."""
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': query,
        'format': 'json',
        'limit': 1,
        'addressdetails': 1,
    }
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'application/json',
    }

    try:
        resp = session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code == 429:
            logger.warning("Nominatim rate limited (429). Triggering fallback geocoder.")
            return None
        if resp.status_code == 403:
            logger.warning("Nominatim access denied (403). Triggering fallback geocoder.")
            return None
        if resp.status_code >= 500:
            logger.warning("Nominatim server error (%s). Triggering fallback geocoder.", resp.status_code)
            return None
        resp.raise_for_status()

        data = resp.json()
        if not data or not isinstance(data, list):
            return None

        result = data[0]
        display_name = result.get('display_name', query)
        lat = float(result['lat'])
        lon = float(result['lon'])
        return {'name': display_name, 'lat': lat, 'lon': lon}

    except requests.exceptions.Timeout:
        logger.warning("Nominatim timed out for query '%s'. Trying fallback.", query)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("Nominatim network error for '%s': %s. Trying fallback.", query, exc)
        return None
    except (ValueError, KeyError, IndexError) as exc:
        logger.warning("Nominatim parsing error for '%s': %s", query, exc)
        return None


def _geocode_open_meteo(query: str, session: requests.Session) -> Optional[Dict[str, Any]]:
    """Fallback geocode query via Open-Meteo Geocoding API."""
    url = 'https://geocoding-api.open-meteo.com/v1/search'
    params = {
        'name': query,
        'count': 1,
        'language': 'en',
        'format': 'json',
    }
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'application/json',
    }

    try:
        resp = session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        if resp.status_code != 200:
            logger.warning("Open-Meteo geocoding HTTP %s", resp.status_code)
            return None

        data = resp.json()
        results = data.get('results', [])
        if not results:
            return None

        item = results[0]
        # Build clean location label e.g. "New York, New York, United States"
        parts = [item.get('name')]
        if item.get('admin1'):
            parts.append(item['admin1'])
        if item.get('country'):
            parts.append(item['country'])
        name = ", ".join(p for p in parts if p)

        return {
            'name': name or query,
            'lat': float(item['latitude']),
            'lon': float(item['longitude']),
        }
    except Exception as exc:
        logger.warning("Open-Meteo geocoder failed for '%s': %s", query, exc)
        return None


def geocode_place(query: str, session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """
    Geocode a place query into standardized {name, lat, lon}.
    Uses memory caching, Nominatim primary provider, and Open-Meteo fallback.
    """
    clean_query = query.strip()
    if not clean_query:
        raise LocationNotFoundError("Empty location query.")

    cache_key = clean_query.lower()
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    sess = session or requests.Session()

    # Try Nominatim primary
    result = _geocode_nominatim(clean_query, sess)

    # If Nominatim returned None, try Open-Meteo fallback
    if result is None:
        result = _geocode_open_meteo(clean_query, sess)

    if result is None:
        raise LocationNotFoundError(f"Could not find geographic coordinates for location: '{clean_query}'")

    # Cache successful lookup
    GEOCODE_CACHE[cache_key] = result
    return result

