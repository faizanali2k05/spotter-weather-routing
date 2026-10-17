export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel';

export interface WeatherData {
  wind_mph: number;
  rain_inches_hr: number;
  snow_inches_hr: number;
}

export interface Checkpoint {
  mile: number;
  lon: number;
  lat: number;
  offset_seconds: number;
  eta: string;
  weather: WeatherData;
  risk: RiskLevel;
  factors: string[];
}

export interface RouteSummary {
  average_risk: number;
  worst_severity: RiskLevel;
  no_travel: boolean;
  miles_by_risk: Record<RiskLevel, number>;
  dominant_hazards: string[];
}

export interface TripRoute {
  id: number;
  distance_miles: number;
  duration_minutes: number;
  arrival: string;
  geometry: [number, number][]; // [lon, lat]
  checkpoints: Checkpoint[];
  summary: RouteSummary;
  recommended: boolean;
  recommendation_reason: string;
}

export interface CorridorPoint {
  lat: number;
  lon: number;
  wind_mph: number;
  rain_inches_hr: number;
  snow_inches_hr: number;
  risk: RiskLevel;
  weight: number;
  dominant_factor: string;
}

export interface CorridorFrame {
  forecast_hour: number;
  valid_time: string;
  points: CorridorPoint[];
}

export interface CorridorHeatmap {
  corridor_stations_count: number;
  forecast_hours: number;
  step_hours: number;
  frames: CorridorFrame[];
}

export interface LocationInfo {
  name: string;
  lat: number;
  lon: number;
}

export interface TripPlan {
  origin: LocationInfo;
  destination: LocationInfo;
  departure: string;
  load_lbs: number;
  spacing_miles: number;
  routes: TripRoute[];
  has_safe_route: boolean;
  corridor_heatmap?: CorridorHeatmap;
  warning: string;
}

export interface PlanRequest {
  origin: string;
  destination: string;
  departure: string;
  load_lbs: number;
  spacing_miles: number;
}

export interface ApiErrorResponse {
  error: string;
  code?: string;
  details?: Record<string, unknown>;
}

