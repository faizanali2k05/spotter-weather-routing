# Spotter Weather-Aware Truck Routing — Known Limitations & Future Work

This document provides transparent, engineering-grade documentation of current system boundaries, provider assumptions, and recommended future enhancements.

---

## 1. Routing Provider Limitations

### 1.1 OSRM Public Demo API Constraints
- **General Vehicle Routing Only:** The default free provider is the public OSRM demonstration server (`router.project-osrm.org`). OSRM computes standard passenger car driving directions and **does not account for commercial trucking constraints**, including:
  - Bridge low-clearance restrictions
  - Gross vehicle weight (GVW) limits
  - Axle weight limits
  - Commercial vehicle parkway bans (e.g. NYC parkways)
  - Hazardous materials (hazmat) transit exclusions
- **Route Alternative Availability:** OSRM does not guarantee three distinct routes for every pair of coordinates. Depending on the highway topography, OSRM may return only 1 or 2 distinct paths. The system never fabricates phantom routes; it presents only genuine alternatives returned by the provider.
- **Enterprise Truck Solution:** We have implemented the `CommercialTruckRoutingProviderAdapter` architectural adapter in `routing/routing_provider.py`. To enable certified truck-restricted routing in production, an enterprise subscription with a dedicated commercial telematics provider (e.g., HERE Fleet Telematics, Mapbox Directions Truck Profile, or Trimble MAPS / PC*MILER) should be connected with vehicle axle/dimension parameters.

---

## 2. Weather Provider & Forecast Horizon

### 2.1 Atmospheric Forecast Horizon
- Open-Meteo hourly models provide up to 5 days (120 hours) of forecast horizon.
- This application bounds planning to a **48-hour departure window** to maintain high forecast confidence and limit weather model divergence.
- Forecasts beyond 48 hours are subject to standard atmospheric uncertainty; long-distance journeys (>1,500 miles) that span multiple days require dynamic in-route replanning.

### 2.2 Microclimates & Mountain Pass Uncertainty
- Open-Meteo utilizes numerical weather prediction (NWP) model grids (e.g. GFS / ECMWF / HRRR). While regional and interstate conditions are accurately captured, hyper-local microclimates (such as sudden mountain pass ice or localized wind gusts in canyons) may vary from model averages.
- The system should always be used as an advisory planning tool alongside official Department of Transportation (DOT) 511 traveler information systems.

---

## 3. Geocoding Rate Limits & Usage Policies

- OpenStreetMap Nominatim enforces strict usage limits (maximum 1 request per second).
- To prevent disruptions, the system implements an automatic fallback to the Open-Meteo Geocoding API and caches repeated lookups in memory.
- In high-throughput production environments, a dedicated enterprise geocoder (e.g. Google Maps Geocoding API, AWS Location Service, or a self-hosted Pelias / Nominatim instance) is recommended.

---

## 4. Planned Architecture Enhancements

1. **Persistent Redis Cache:** Replace the in-memory coordinate cache with Redis for distributed multi-worker caching across scaled Render backend containers.
2. **Turn-by-Turn Truck Speed Segments:** Incorporate road-segment specific heavy vehicle speed profiles (e.g. 55 mph highway limit vs passenger car 70 mph) to refine checkpoint ETA calculations.
3. **Severe Weather Push Alerts:** Webhook or WebSocket alerts dispatched to fleet managers when sudden storm fronts intersect active in-transit routes.

