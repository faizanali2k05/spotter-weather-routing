"""
Corridor Weather Heatmap Service.
Generates a spatially distributed grid around the planned travel corridor,
retrieves 48-hour forecasts, and provides time-dependent risk intensity frames
for MapLibre GL heatmap rendering.
"""
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import requests

from .weather_service import fetch_batch_forecasts, interpolate_weather_at_eta
from .risk import classify_detailed

# Risk weight map for heatmap rendering (0.0 to 1.0)
RISK_WEIGHTS = {
    'Low': 0.15,
    'Moderate': 0.45,
    'High': 0.70,
    'Severe': 0.90,
    'No Travel': 1.00,
}


def haversine_miles(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Distance in miles between two (lat, lon) coordinates."""
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * math.asin(min(1.0, math.sqrt(a)))


def generate_corridor_grid(routes: List[Dict[str, Any]], max_grid_points: int = 16) -> List[Tuple[float, float]]:
    """
    Generate an evenly distributed grid of sample coordinates surrounding the route corridors.
    Samples within a buffer envelope of ~30 miles from the actual route geometries.
    """
    all_coords = []
    for r in routes:
        all_coords.extend(r.get('geometry', []))

    if not all_coords:
        return []

    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Padding in degrees (~25-30 miles)
    pad_lat = 0.40
    pad_lon = 0.45

    b_min_lat = min_lat - pad_lat
    b_max_lat = max_lat + pad_lat
    b_min_lon = min_lon - pad_lon
    b_max_lon = max_lon + pad_lon

    # Subsample route points for proximity testing
    step = max(1, len(all_coords) // 40)
    route_samples = [(c[1], c[0]) for c in all_coords[::step]]

    # Determine grid resolution
    lat_span = max(0.1, b_max_lat - b_min_lat)
    lon_span = max(0.1, b_max_lon - b_min_lon)
    aspect = lon_span / lat_span

    # Compute num rows and cols approximately proportional to aspect ratio
    grid_cols = max(3, min(6, int(round(math.sqrt(max_grid_points * aspect)))))
    grid_rows = max(3, min(6, int(round(max_grid_points / grid_cols))))

    candidate_grid = []
    for r_idx in range(grid_rows):
        lat = b_min_lat + (r_idx / max(1, grid_rows - 1)) * (b_max_lat - b_min_lat)
        for c_idx in range(grid_cols):
            lon = b_min_lon + (c_idx / max(1, grid_cols - 1)) * (b_max_lon - b_min_lon)
            candidate_grid.append((round(lat, 2), round(lon, 2)))

    # Filter candidates to only those within ~45 miles of the route polyline
    filtered = []
    for pt in candidate_grid:
        min_dist = min(haversine_miles(pt, r_pt) for r_pt in route_samples)
        if min_dist <= 50.0:  # within 50 miles of route
            filtered.append(pt)

    # If filter was too strict, ensure at least bounding centers
    if len(filtered) < 4:
        filtered = candidate_grid[:max_grid_points]

    return filtered[:max_grid_points]


def build_corridor_heatmap(
    routes: List[Dict[str, Any]],
    departure_time: datetime,
    load_lbs: float,
    session: Optional[requests.Session] = None,
    forecast_hours: int = 48,
    hour_step: int = 3,
) -> Dict[str, Any]:
    """
    Build spatial corridor heatmap dataset for hours 0 to 48.
    hour_step of 3 gives 17 temporal frames (0h, 3h, 6h, ..., 48h) providing smooth timeline scrubbing
    with compact payload size.
    """
    grid_coords = generate_corridor_grid(routes)
    if not grid_coords:
        return {'grid_points': [], 'frames': []}

    forecast_map = fetch_batch_forecasts(grid_coords, session=session)

    frames = []
    utc_dep = departure_time.astimezone(timezone.utc)

    for h_offset in range(0, forecast_hours + 1, hour_step):
        frame_time = utc_dep + timedelta(hours=h_offset)
        points_data = []

        for pt in grid_coords:
            hourly = forecast_map.get(pt)
            if not hourly:
                continue

            try:
                weather = interpolate_weather_at_eta(hourly, frame_time)
                risk_lvl, factors = classify_detailed(
                    weather['wind_mph'],
                    weather['rain_inches_hr'],
                    weather['snow_inches_hr'],
                    load_lbs,
                )
                points_data.append({
                    'lat': pt[0],
                    'lon': pt[1],
                    'wind_mph': weather['wind_mph'],
                    'rain_inches_hr': weather['rain_inches_hr'],
                    'snow_inches_hr': weather['snow_inches_hr'],
                    'risk': risk_lvl,
                    'weight': RISK_WEIGHTS.get(risk_lvl, 0.2),
                    'dominant_factor': factors[0] if factors else 'Optimal',
                })
            except Exception:
                continue

        frames.append({
            'forecast_hour': h_offset,
            'valid_time': frame_time.isoformat(),
            'points': points_data,
        })

    return {
        'corridor_stations_count': len(grid_coords),
        'forecast_hours': forecast_hours,
        'step_hours': hour_step,
        'frames': frames,
    }
