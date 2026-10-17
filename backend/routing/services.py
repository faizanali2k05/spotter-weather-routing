"""
Route planning orchestrator.
Coordinates geocoding, multi-alternative routing, checkpoint resampling,
batched weather forecasting, risk evaluation, route ranking, and corridor heatmaps.
"""
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import requests

from .exceptions import InputValidationError, ForecastHorizonError, RouteNotFoundError
from .geocoding import geocode_place
from .routing_provider import get_routing_provider
from .weather_service import get_weather_for_checkpoints
from .risk import classify_detailed, summarize, ranking_key, build_recommendation_reason
from .corridor_service import build_corridor_heatmap

logger = logging.getLogger('spotter.services')

MILES_PER_METER = 1.0 / 1609.344


def interpolate_coordinate(a: List[float], b: List[float], t: float) -> List[float]:
    """Linear interpolation between two [lon, lat] coordinates."""
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]


def haversine_miles(coord1: List[float], coord2: List[float]) -> float:
    """Great-circle distance in miles between two [lon, lat] points."""
    lon1, lat1 = map(math.radians, coord1)
    lon2, lat2 = map(math.radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * math.asin(min(1.0, math.sqrt(a)))


def route_checkpoints(coordinates: List[List[float]], duration_seconds: float, spacing_miles: int) -> List[Dict[str, Any]]:
    """
    Resample the full polyline at uniform distance intervals (10, 25, or 50 miles),
    always preserving the route origin (mile 0) and final destination (total miles).
    ETAs are computed proportional to progress along cumulative travel distance.
    """
    if not coordinates:
        return []
    if len(coordinates) == 1:
        return [{'mile': 0.0, 'lon': coordinates[0][0], 'lat': coordinates[0][1], 'offset_seconds': 0}]

    segments = [haversine_miles(coordinates[i], coordinates[i + 1]) for i in range(len(coordinates) - 1)]
    cumulative = [0.0]
    for seg in segments:
        cumulative.append(cumulative[-1] + seg)
    total_miles = cumulative[-1]

    # Generate target milestone distances
    targets = [0.0]
    cur_m = float(spacing_miles)
    while cur_m < total_miles - 0.5:
        targets.append(cur_m)
        cur_m += float(spacing_miles)
    if total_miles > 0.05:
        targets.append(total_miles)

    results = []
    seg_idx = 0
    num_segs = len(segments)

    for target in targets:
        while seg_idx < num_segs - 1 and cumulative[seg_idx + 1] < target:
            seg_idx += 1

        seg_len = segments[seg_idx] if num_segs > 0 else 0.0
        ratio = (target - cumulative[seg_idx]) / seg_len if seg_len > 0.0001 else 0.0
        ratio = max(0.0, min(1.0, ratio))

        pt = interpolate_coordinate(coordinates[seg_idx], coordinates[seg_idx + 1], ratio)
        offset = round(duration_seconds * (target / total_miles)) if total_miles > 0 else 0

        results.append({
            'mile': round(target, 1),
            'lon': round(pt[0], 5),
            'lat': round(pt[1], 5),
            'offset_seconds': offset,
        })

    return results


def build_plan(
    origin_text: str,
    destination_text: str,
    departure_str: str,
    load_lbs: float,
    spacing_miles: int,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Execute end-to-end trip planning workflow:
      1. Geocode origin and destination.
      2. Validate departure timestamp timezone and horizon.
      3. Retrieve road network routes from provider.
      4. Resample checkpoints and compute arrival times.
      5. Fetch batched weather forecasts along all checkpoints.
      6. Classify load-dependent risk and summarize route exposures.
      7. Rank routes and generate recommendation explanation.
      8. Generate spatial corridor heatmap across 0-48h horizon.
    """
    sess = session or requests.Session()

    # Geocoding
    origin = geocode_place(origin_text, session=sess)
    destination = geocode_place(destination_text, session=sess)

    # Validate departure
    try:
        base_dt = datetime.fromisoformat(departure_str.replace('Z', '+00:00'))
    except Exception as exc:
        raise InputValidationError(f"Invalid departure format: '{departure_str}'. Expected ISO 8601.") from exc

    if base_dt.tzinfo is None:
        raise InputValidationError("Departure time must include an explicit timezone offset.")

    now = datetime.now(timezone.utc)
    if base_dt < now - timedelta(minutes=30):
        raise InputValidationError("Departure time cannot be in the past.")
    if base_dt > now + timedelta(hours=48):
        raise ForecastHorizonError("Departure time must be within the 48-hour forecast horizon.")

    # Retrieve routes
    provider = get_routing_provider()
    raw_routes = provider.get_routes(origin, destination)
    if not raw_routes:
        raise RouteNotFoundError(f"No routes available between {origin['name']} and {destination['name']}.")

    processed_routes = []
    for idx, r in enumerate(raw_routes):
        geometry = r['geometry']
        duration = r['duration_seconds']
        distance = r['distance_meters'] * MILES_PER_METER

        checkpoints = route_checkpoints(geometry, duration, spacing_miles)
        etas = [base_dt + timedelta(seconds=p['offset_seconds']) for p in checkpoints]

        # Batched weather fetching
        forecasts = get_weather_for_checkpoints(checkpoints, etas, session=sess)

        enriched_checkpoints = []
        for pt, eta, fc in zip(checkpoints, etas, forecasts):
            risk_level, factors = classify_detailed(
                fc['wind_mph'],
                fc['rain_inches_hr'],
                fc['snow_inches_hr'],
                load_lbs,
            )
            enriched_checkpoints.append({
                'mile': pt['mile'],
                'lon': pt['lon'],
                'lat': pt['lat'],
                'offset_seconds': pt['offset_seconds'],
                'eta': eta.isoformat(),
                'weather': fc,
                'risk': risk_level,
                'factors': factors,
            })

        summary = summarize(enriched_checkpoints, distance)

        processed_routes.append({
            'id': idx + 1,
            'distance_miles': round(distance, 1),
            'duration_minutes': round(duration / 60.0),
            'arrival': (base_dt + timedelta(seconds=duration)).isoformat(),
            'geometry': geometry,
            'checkpoints': enriched_checkpoints,
            'summary': summary,
            'recommended': False,
            'recommendation_reason': '',
        })

    # Sort routes by multi-dimensional safety ranking
    processed_routes.sort(key=ranking_key)

    has_safe_route = any(not r['summary']['no_travel'] for r in processed_routes)
    for rank, route in enumerate(processed_routes):
        is_rec = (rank == 0 and not route['summary']['no_travel'])
        route['recommended'] = is_rec
        route['recommendation_reason'] = build_recommendation_reason(route, processed_routes)

    # Build spatial corridor heatmap dataset
    corridor_heatmap = build_corridor_heatmap(
        processed_routes,
        base_dt,
        load_lbs,
        session=sess,
        forecast_hours=48,
        hour_step=3,
    )

    advisory_warning = (
        "Routes use OSRM general driving directions and are NOT certified for commercial truck height/weight/hazmat restrictions. "
        "Weather estimates and ETAs are advisory only. Always check local DOT road conditions before departure."
    )
    if not has_safe_route:
        advisory_warning = (
            "DANGER: All available routes encounter No Travel weather conditions. "
            "Dispatch should be suspended or delayed until severe weather subsides."
        )

    return {
        'origin': origin,
        'destination': destination,
        'departure': base_dt.isoformat(),
        'load_lbs': load_lbs,
        'spacing_miles': spacing_miles,
        'routes': processed_routes,
        'has_safe_route': has_safe_route,
        'corridor_heatmap': corridor_heatmap,
        'warning': advisory_warning,
    }
