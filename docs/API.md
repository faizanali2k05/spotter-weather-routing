# Spotter Weather-Aware Truck Routing — API Specification

**Base URL (Local):** `http://localhost:8000`  
**Base URL (Production):** `https://spotter-weather-routing-api.onrender.com`  
**Protocol:** HTTP/1.1 or HTTP/2 over TLS  
**Format:** JSON (`application/json`)

---

## 1. Endpoints

### 1.1 Health Check

```http
GET /api/health/
```

Checks API readiness, version, and external provider connectivity.

#### Response `200 OK`
```json
{
  "status": "ok",
  "service": "spotter-weather-routing-api",
  "version": "2.0.0",
  "timestamp": "2026-10-18T10:00:00.000000+00:00",
  "routing_provider": "OSRM (Demo)",
  "weather_provider": "Open-Meteo"
}
```

---

### 1.2 Geocode Location

```http
GET /api/geocode/?q={location_name}
```

Geocodes a human-readable city or place name into geographic coordinates. Uses OpenStreetMap Nominatim with automatic fallback to Open-Meteo Geocoding API.

#### Query Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `q` | `string` | **Yes** | City name or address (min 2 characters, max 180). |

#### Response `200 OK`
```json
{
  "name": "New York, United States",
  "lat": 40.7127,
  "lon": -74.0060
}
```

#### Error Responses
- **`400 Bad Request`**: Missing query parameter or string too short (`< 2` chars).
- **`404 Not Found`**: Specified location could not be located on any geocoding provider.

---

### 1.3 Plan Weather-Aware Trip

```http
POST /api/plan/
Content-Type: application/json
```

Calculates up to 3 driving route alternatives, resamples checkpoints at uniform intervals (10, 25, or 50 miles), retrieves arrival-time weather forecasts, evaluates load-dependent risk thresholds, ranks routes, and generates a spatial corridor weather heatmap across a 48-hour horizon.

#### Request Body
```json
{
  "origin": "New York, NY",
  "destination": "Philadelphia, PA",
  "departure": "2026-10-18T14:00:00Z",
  "load_lbs": 35000,
  "spacing_miles": 25
}
```

#### Parameters
| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `origin` | `string` | **Yes** | 2–180 chars | Origin city or address. |
| `destination` | `string` | **Yes** | 2–180 chars | Destination city or address. |
| `departure` | `string` | **Yes** | ISO 8601 UTC / Offset | Departure time (cannot be in past; max +48h). |
| `load_lbs` | `number` | No | 0 to 100,000 (default 0) | Cargo weight in pounds. |
| `spacing_miles` | `integer` | No | 10, 25, or 50 (default 25) | Distance between weather checkpoints. |

#### Response `200 OK`
```json
{
  "origin": {
    "name": "New York, United States",
    "lat": 40.7127,
    "lon": -74.0060
  },
  "destination": {
    "name": "Philadelphia, Pennsylvania, United States",
    "lat": 39.9526,
    "lon": -75.1652
  },
  "departure": "2026-10-18T14:00:00+00:00",
  "load_lbs": 35000.0,
  "spacing_miles": 25,
  "has_safe_route": true,
  "warning": "Routes use OSRM general driving directions and are NOT certified for commercial truck restrictions.",
  "routes": [
    {
      "id": 1,
      "distance_miles": 94.6,
      "duration_minutes": 126,
      "arrival": "2026-10-18T16:06:00+00:00",
      "recommended": true,
      "recommendation_reason": "Recommended route: optimal conditions with 0 severe/high weather risk miles along the entire 95-mile corridor.",
      "summary": {
        "average_risk": 0.0,
        "worst_severity": "Low",
        "no_travel": false,
        "miles_by_risk": {
          "Low": 94.6,
          "Moderate": 0.0,
          "High": 0.0,
          "Severe": 0.0,
          "No Travel": 0.0
        },
        "dominant_hazards": []
      },
      "geometry": [
        [-74.0060, 40.7127],
        [-74.2541, 40.5892],
        [-75.1652, 39.9526]
      ],
      "checkpoints": [
        {
          "mile": 0.0,
          "lon": -74.0060,
          "lat": 40.7127,
          "offset_seconds": 0,
          "eta": "2026-10-18T14:00:00+00:00",
          "weather": {
            "wind_mph": 14.5,
            "rain_inches_hr": 0.0,
            "snow_inches_hr": 0.0
          },
          "risk": "Low",
          "factors": ["Clear / optimal driving conditions"]
        }
      ]
    }
  ],
  "corridor_heatmap": {
    "corridor_stations_count": 16,
    "forecast_hours": 48,
    "step_hours": 3,
    "frames": [
      {
        "forecast_hour": 0,
        "valid_time": "2026-10-18T14:00:00+00:00",
        "points": [
          {
            "lat": 40.71,
            "lon": -74.01,
            "wind_mph": 14.5,
            "rain_inches_hr": 0.0,
            "snow_inches_hr": 0.0,
            "risk": "Low",
            "weight": 0.15,
            "dominant_factor": "Clear / optimal driving conditions"
          }
        ]
      }
    ]
  }
}
```

---

## 2. Standardized Error Response Schema

All non-200 responses return a consistent, sanitized error structure:

```json
{
  "error": "Descriptive human-readable explanation of error",
  "code": "ERROR_CODE_IDENTIFIER",
  "details": {}
}
```

### Error Codes and HTTP Statuses
| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `VALIDATION_ERROR` | Invalid input parameter (e.g. invalid spacing, past departure, load `> 100k`). |
| `400 Bad Request` | `FORECAST_HORIZON_EXCEEDED` | Departure or arrival extends beyond supported 48-hour forecast horizon. |
| `404 Not Found` | `LOCATION_NOT_FOUND` | Geocoding was unable to find coordinates for origin or destination. |
| `404 Not Found` | `ROUTE_NOT_FOUND` | No drivable road network path exists between the given coordinates. |
| `429 Too Many Requests`| `PROVIDER_RATE_LIMIT` | External provider rate limit reached; client should back off and retry. |
| `502 Bad Gateway` | `PROVIDER_NETWORK_ERROR` | External provider unreachable or returned network connectivity failure. |
| `502 Bad Gateway` | `PROVIDER_MALFORMED_RESPONSE` | External provider returned invalid or unparseable payload. |
| `504 Gateway Timeout` | `PROVIDER_TIMEOUT` | Routing or weather provider request exceeded timeout threshold. |
| `500 Internal Error` | `INTERNAL_SERVER_ERROR` | Unhandled server exception (logged server-side without leaking secrets). |
