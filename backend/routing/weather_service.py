"""
Weather forecast service utilizing Open-Meteo.
Features:
- Batched multi-coordinate API requests
- Rounded-coordinate in-memory TTL caching
- Accurate unit handling (mph for wind, inches/hr for precipitation and snowfall)
- Timezone-aware UTC ETA alignment
- Safe error handling and missing-data reporting
"""
import logging
import math
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import requests

from .exceptions import (
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderNetworkError,
    MalformedProviderResponseError,
    ForecastHorizonError,
)

logger = logging.getLogger('spotter.weather')

DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; SpotterWeatherRouting/2.0; +https://github.com/faizanali2k05/spotter-weather-routing)'
OPEN_METEO_BASE_URL = 'https://api.open-meteo.com/v1/forecast'
REQUEST_TIMEOUT_SECONDS = 25
MAX_RETRIES = 2
CACHE_TTL_SECONDS = 900  # 15 minutes
BATCH_CHUNK_SIZE = 30

# Cache entry: (timestamp, hourly_dict)
WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}


def clear_expired_weather_cache():
    """Prune expired weather cache entries."""
    now = time.time()
    expired_keys = [k for k, (ts, _) in WEATHER_CACHE.items() if now - ts > CACHE_TTL_SECONDS]
    for k in expired_keys:
        del WEATHER_CACHE[k]


def get_cached_forecast(lat_key: float, lon_key: float) -> Optional[Dict[str, Any]]:
    entry = WEATHER_CACHE.get((lat_key, lon_key))
    if entry:
        ts, data = entry
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data
    return None


def set_cached_forecast(lat_key: float, lon_key: float, data: Dict[str, Any]):
    WEATHER_CACHE[(lat_key, lon_key)] = (time.time(), data)


def fetch_batch_forecasts(coords: List[Tuple[float, float]], session: Optional[requests.Session] = None) -> Dict[Tuple[float, float], Dict[str, Any]]:
    """
    Fetch forecasts for a list of rounded (lat, lon) coordinates in batches.
    Returns mapping from (lat, lon) to Open-Meteo hourly forecast dict.
    """
    if not coords:
        return {}

    sess = session or requests.Session()
    results: Dict[Tuple[float, float], Dict[str, Any]] = {}
    missing_coords: List[Tuple[float, float]] = []

    for c in coords:
        cached = get_cached_forecast(c[0], c[1])
        if cached:
            results[c] = cached
        else:
            missing_coords.append(c)

    if not missing_coords:
        return results

    # Chunk missing coordinates to respect query string lengths and provider limits
    for i in range(0, len(missing_coords), BATCH_CHUNK_SIZE):
        chunk = missing_coords[i:i + BATCH_CHUNK_SIZE]
        lats_str = ",".join(f"{c[0]:.2f}" for c in chunk)
        lons_str = ",".join(f"{c[1]:.2f}" for c in chunk)

        params = {
            'latitude': lats_str,
            'longitude': lons_str,
            'hourly': 'wind_speed_10m,rain,snowfall',
            'wind_speed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'GMT',
            'forecast_days': 5,
        }
        headers = {
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept': 'application/json',
        }

        chunk_success = False
        last_chunk_exc = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = sess.get(OPEN_METEO_BASE_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
                if resp.status_code == 429:
                    raise ProviderRateLimitError("Open-Meteo weather API rate limit exceeded.")
                if resp.status_code == 503 or resp.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        time.sleep(0.6 * (2 ** attempt))
                        continue
                    raise ProviderNetworkError(f"Open-Meteo service returned HTTP {resp.status_code}.")
                resp.raise_for_status()

                payload = resp.json()

                if isinstance(payload, list):
                    forecast_items = payload
                elif isinstance(payload, dict) and 'hourly' in payload:
                    forecast_items = [payload]
                else:
                    raise MalformedProviderResponseError("Open-Meteo returned unexpected payload structure.")

                for coord, item in zip(chunk, forecast_items):
                    hourly = item.get('hourly', {})
                    results[coord] = hourly
                    set_cached_forecast(coord[0], coord[1], hourly)

                chunk_success = True
                break

            except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as exc:
                last_chunk_exc = ProviderTimeoutError("Weather provider request timed out.")
                if attempt < MAX_RETRIES:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise last_chunk_exc from exc
            except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as exc:
                last_chunk_exc = ProviderNetworkError(f"Weather provider network connection failed: {str(exc)}")
                if attempt < MAX_RETRIES:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise last_chunk_exc from exc
            except (ProviderRateLimitError, MalformedProviderResponseError):
                raise
            except Exception as exc:
                last_chunk_exc = ProviderNetworkError(f"Error fetching weather forecast: {str(exc)}")
                if attempt < MAX_RETRIES:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise last_chunk_exc from exc

        if not chunk_success and last_chunk_exc:
            raise last_chunk_exc

    return results


def interpolate_weather_at_eta(hourly: Dict[str, Any], eta: datetime) -> Dict[str, float]:
    """
    Given Open-Meteo hourly data and a timezone-aware ETA,
    locate or interpolate the weather conditions.
    Units:
      - wind_mph: mph
      - rain_inches_hr: inches/hr
      - snow_inches_hr: inches/hr (accurate direct units)
    """
    utc_eta = eta.astimezone(timezone.utc)
    times = hourly.get('time', [])
    if not times:
        raise MalformedProviderResponseError("Weather hourly timeline is empty.")

    # Convert times to datetime objects
    # Open-Meteo time strings are ISO: 'YYYY-MM-DDTHH:00'
    base_time_str = times[0]
    try:
        t0 = datetime.fromisoformat(base_time_str).replace(tzinfo=timezone.utc)
    except Exception:
        t0 = datetime.strptime(base_time_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)

    # Hourly index
    hours_diff = (utc_eta - t0).total_seconds() / 3600.0

    if hours_diff < 0:
        # Checkpoint ETA is slightly in the past (e.g. just started)
        idx_low = 0
        idx_high = 0
        frac = 0.0
    elif hours_diff >= len(times) - 1:
        if hours_diff > len(times) + 1:
            raise ForecastHorizonError(
                f"Checkpoint ETA ({utc_eta.isoformat()}) exceeds available forecast horizon ({times[-1]})."
            )
        idx_low = len(times) - 1
        idx_high = len(times) - 1
        frac = 0.0
    else:
        idx_low = int(math.floor(hours_diff))
        idx_high = min(len(times) - 1, idx_low + 1)
        frac = hours_diff - idx_low

    def get_val(key: str, idx: int) -> float:
        val = hourly.get(key, [])[idx]
        return float(val) if val is not None else 0.0

    wind_low = get_val('wind_speed_10m', idx_low)
    wind_high = get_val('wind_speed_10m', idx_high)
    wind_mph = wind_low + (wind_high - wind_low) * frac

    rain_low = get_val('rain', idx_low)
    rain_high = get_val('rain', idx_high)
    rain_in = rain_low + (rain_high - rain_low) * frac

    snow_low = get_val('snowfall', idx_low)
    snow_high = get_val('snowfall', idx_high)
    # Direct inches/hr — NO division by 2.54!
    snow_in = snow_low + (snow_high - snow_low) * frac

    return {
        'wind_mph': round(max(0.0, wind_mph), 1),
        'rain_inches_hr': round(max(0.0, rain_in), 3),
        'snow_inches_hr': round(max(0.0, snow_in), 3),
    }


def get_weather_for_checkpoints(checkpoints: List[Dict[str, Any]], etas: List[datetime], session: Optional[requests.Session] = None) -> List[Dict[str, float]]:
    """
    Retrieve weather for a list of checkpoints and arrival times using batched requests.
    """
    coords_keys = [(round(p['lat'], 2), round(p['lon'], 2)) for p in checkpoints]
    unique_coords = list(set(coords_keys))

    forecast_map = fetch_batch_forecasts(unique_coords, session=session)

    results = []
    for point, eta, key in zip(checkpoints, etas, coords_keys):
        hourly = forecast_map.get(key)
        if not hourly:
            raise ProviderNetworkError(f"Missing forecast for checkpoint at {key}")
        weather = interpolate_weather_at_eta(hourly, eta)
        results.append(weather)

    return results
