"""
Deterministic, auditable weather and load-dependent risk evaluation engine
conforming to Spotter's commercial trucking standards.
"""
from typing import List, Dict, Any, Tuple

LEVELS = ['Low', 'Moderate', 'High', 'Severe', 'No Travel']
LEVEL_INDEX = {name: i for i, name in enumerate(LEVELS)}


def classify_wind(wind_mph: float, load_lbs: float) -> Tuple[int, List[str]]:
    """
    Wind thresholds (mph):
      Low: < 25
      Moderate: 25–34 (< 35)
      High: 35–44 (< 45)
      Severe: 45–54 (< 55)
      No Travel: 55+ (>= 55)

    Load-dependent wind modifiers:
      - Wind 45–54 mph and load > 30,000 lb: No Travel
      - Wind 35–44 mph and load > 40,000 lb: Severe
    """
    factors = []
    if wind_mph < 25:
        level = 0
    elif wind_mph < 35:
        level = 1
        factors.append(f"Moderate wind ({wind_mph:.1f} mph)")
    elif wind_mph < 45:
        if load_lbs > 40000:
            level = 3  # Severe due to heavy load
            factors.append(f"High wind ({wind_mph:.1f} mph) with heavy load ({load_lbs:,.0f} lb) => Severe")
        else:
            level = 2
            factors.append(f"High wind ({wind_mph:.1f} mph)")
    elif wind_mph < 55:
        if load_lbs > 30000:
            level = 4  # No Travel due to load
            factors.append(f"Severe wind ({wind_mph:.1f} mph) with load > 30k lb ({load_lbs:,.0f} lb) => No Travel")
        else:
            level = 3
            factors.append(f"Severe wind ({wind_mph:.1f} mph)")
    else:
        level = 4
        factors.append(f"Extreme wind ({wind_mph:.1f} mph >= 55 mph) => No Travel")

    return level, factors


def classify_rain(rain_inches_hr: float) -> Tuple[int, List[str]]:
    """
    Rain thresholds (inches/hour):
      Low: < 0.10
      Moderate: 0.10 to < 0.25
      High: 0.25 to < 0.50
      Severe: 0.50 to 1.00 (inclusive)
      No Travel: > 1.00
    """
    factors = []
    if rain_inches_hr < 0.10:
        level = 0
    elif rain_inches_hr < 0.25:
        level = 1
        factors.append(f"Moderate rain ({rain_inches_hr:.2f} in/hr)")
    elif rain_inches_hr < 0.50:
        level = 2
        factors.append(f"Heavy rain ({rain_inches_hr:.2f} in/hr)")
    elif rain_inches_hr <= 1.00:
        level = 3
        factors.append(f"Torrential rain ({rain_inches_hr:.2f} in/hr)")
    else:
        level = 4
        factors.append(f"Extreme rainfall ({rain_inches_hr:.2f} in/hr > 1.00) => No Travel")

    return level, factors


def classify_snow(snow_inches_hr: float) -> Tuple[int, List[str]]:
    """
    Snow thresholds (inches/hour):
      Low: < 0.5
      Moderate: 0.5 to < 1.0
      High: 1.0 to < 2.0
      Severe: 2.0 to 3.0 (inclusive)
      No Travel: > 3.0
    """
    factors = []
    if snow_inches_hr < 0.5:
        level = 0
    elif snow_inches_hr < 1.0:
        level = 1
        factors.append(f"Moderate snow ({snow_inches_hr:.2f} in/hr)")
    elif snow_inches_hr < 2.0:
        level = 2
        factors.append(f"Heavy snow ({snow_inches_hr:.2f} in/hr)")
    elif snow_inches_hr <= 3.0:
        level = 3
        factors.append(f"Blizzard-intensity snow ({snow_inches_hr:.2f} in/hr)")
    else:
        level = 4
        factors.append(f"Extreme snowfall ({snow_inches_hr:.2f} in/hr > 3.00) => No Travel")

    return level, factors


def classify(wind_mph: float, rain_inches_hr: float, snow_inches_hr: float, load_lbs: float) -> str:
    """Classify overall risk level as a string for backward compatibility."""
    risk_level, _ = classify_detailed(wind_mph, rain_inches_hr, snow_inches_hr, load_lbs)
    return risk_level


def classify_detailed(wind_mph: float, rain_inches_hr: float, snow_inches_hr: float, load_lbs: float) -> Tuple[str, List[str]]:
    """Return risk level string and all contributing hazard descriptions."""
    w_lvl, w_factors = classify_wind(wind_mph, load_lbs)
    r_lvl, r_factors = classify_rain(rain_inches_hr)
    s_lvl, s_factors = classify_snow(snow_inches_hr)

    overall_level = max(w_lvl, r_lvl, s_lvl)
    all_factors = []
    if w_lvl == overall_level and w_factors:
        all_factors.extend(w_factors)
    if r_lvl == overall_level and r_factors:
        all_factors.extend(r_factors)
    if s_lvl == overall_level and s_factors:
        all_factors.extend(s_factors)

    if not all_factors:
        all_factors.append("Clear / optimal driving conditions")

    return LEVELS[overall_level], all_factors


def summarize(checkpoints: List[Dict[str, Any]], distance_miles: float) -> Dict[str, Any]:
    """
    Calculate mileage exposed to each severity level using midpoint sampling intervals,
    compute distance-weighted average risk index, worst severity, and dominant hazards.
    """
    totals = {name: 0.0 for name in LEVELS}
    dominant_hazards_set = set()

    n = len(checkpoints)
    if n == 0:
        return {
            'miles_by_risk': totals,
            'average_risk': 0.0,
            'worst_severity': 'Low',
            'no_travel': False,
            'dominant_hazards': [],
        }

    for i, point in enumerate(checkpoints):
        left = 0.0 if i == 0 else (checkpoints[i - 1]['mile'] + point['mile']) / 2.0
        right = distance_miles if i == n - 1 else (point['mile'] + checkpoints[i + 1]['mile']) / 2.0
        seg_miles = max(0.0, right - left)
        risk_name = point.get('risk', 'Low')
        totals[risk_name] += seg_miles

        if point.get('risk') in ('High', 'Severe', 'No Travel'):
            for factor in point.get('factors', []):
                dominant_hazards_set.add(factor)

    total_miles = sum(totals.values())
    if total_miles > 0:
        mean_risk = sum(LEVEL_INDEX[lvl] * totals[lvl] for lvl in LEVELS) / total_miles
    else:
        mean_risk = 0.0

    worst_idx = 0
    for lvl in reversed(LEVELS):
        if totals[lvl] > 0.001:
            worst_idx = LEVEL_INDEX[lvl]
            break

    return {
        'miles_by_risk': {k: round(v, 1) for k, v in totals.items()},
        'average_risk': round(mean_risk, 3),
        'worst_severity': LEVELS[worst_idx],
        'no_travel': totals['No Travel'] > 0.001,
        'dominant_hazards': sorted(list(dominant_hazards_set)),
    }


def ranking_key(route: Dict[str, Any]) -> Tuple[int, float, float, float, float, float]:
    """
    Multi-dimensional ranking key:
      1. Has No Travel exposure (0 = False, 1 = True)
      2. Severe exposure mileage (ascending)
      3. High exposure mileage (ascending)
      4. Distance-weighted average risk (ascending)
      5. Travel duration in minutes (ascending)
      6. Total distance in miles (ascending)
    """
    summary = route['summary']
    miles = summary['miles_by_risk']
    no_travel_flag = 1 if summary['no_travel'] else 0
    severe_miles = float(miles.get('Severe', 0.0))
    high_miles = float(miles.get('High', 0.0))
    avg_risk = float(summary.get('average_risk', 0.0))
    duration = float(route.get('duration_minutes', 0))
    distance = float(route.get('distance_miles', 0))

    return (no_travel_flag, severe_miles, high_miles, avg_risk, duration, distance)


def build_recommendation_reason(route: Dict[str, Any], all_routes: List[Dict[str, Any]]) -> str:
    """Generate clear, human-readable rationale for why this route was selected or travel was suspended."""
    summary = route['summary']
    if summary['no_travel']:
        hazards = ", ".join(summary['dominant_hazards'][:2]) or "Severe weather threshold exceeded"
        return f"Not recommended for dispatch: contains No Travel condition ({hazards}). Postpone departure."

    miles = summary['miles_by_risk']
    severe = miles.get('Severe', 0.0)
    high = miles.get('High', 0.0)

    if severe == 0 and high == 0:
        return f"Recommended route: optimal conditions with 0 severe/high weather risk miles along the entire {route['distance_miles']:.0f}-mile corridor."
    elif severe == 0:
        return f"Recommended route: avoids all severe/no-travel hazards; limited to {high:.0f} miles of moderate/high exposure."
    else:
        return f"Recommended route: minimizes severe weather exposure ({severe:.0f} mi) compared to available alternatives."
