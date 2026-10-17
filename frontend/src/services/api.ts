import { TripPlan, PlanRequest, LocationInfo } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, status: number = 500, code: string = 'API_ERROR', details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export async function fetchHealth(): Promise<{ status: string; service: string; version: string }> {
  const resp = await fetch(`${API_BASE_URL}/api/health/`);
  if (!resp.ok) {
    throw new ApiError(`Health check failed with status ${resp.status}`, resp.status);
  }
  return resp.json();
}

export async function geocodeLocation(query: string): Promise<LocationInfo> {
  const params = new URLSearchParams({ q: query.trim() });
  const resp = await fetch(`${API_BASE_URL}/api/geocode/?${params.toString()}`);
  const data = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    throw new ApiError(
      data.error || `Geocoding failed (${resp.status})`,
      resp.status,
      data.code || 'GEOCODE_ERROR',
      data.details
    );
  }
  return data;
}

export async function requestTripPlan(request: PlanRequest): Promise<TripPlan> {
  const resp = await fetch(`${API_BASE_URL}/api/plan/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(request),
  });

  const data = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    throw new ApiError(
      data.error || `Trip planning failed (${resp.status})`,
      resp.status,
      data.code || 'PLAN_ERROR',
      data.details
    );
  }

  return data;
}

