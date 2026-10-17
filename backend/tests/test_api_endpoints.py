import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


class TestApiEndpoints:
    def test_health_endpoint(self, client):
        resp = client.get('/api/health/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        assert data['service'] == 'spotter-weather-routing-api'
        assert 'version' in data
        assert 'timestamp' in data

    def test_cors_preflight_options(self, client):
        resp = client.options(
            '/api/plan/',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
        )
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Origin') == 'http://localhost:5173'

    def test_cors_127_0_0_1_allowed(self, client):
        resp = client.options(
            '/api/plan/',
            HTTP_ORIGIN='http://127.0.0.1:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
        )
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Origin') == 'http://127.0.0.1:5173'

    def test_cors_vercel_preview_allowed(self, client):
        resp = client.options(
            '/api/plan/',
            HTTP_ORIGIN='https://spotter-weather-routing-git-branch-faizan.vercel.app',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type',
        )
        assert resp.status_code == 200
        assert resp.headers.get('Access-Control-Allow-Origin') == 'https://spotter-weather-routing-git-branch-faizan.vercel.app'

    def test_geocode_validation_missing_query(self, client):
        resp = client.get('/api/geocode/')
        assert resp.status_code == 400
        data = resp.json()
        assert 'error' in data

    @patch('routing.views.geocode_place')
    def test_geocode_success(self, mock_geocode, client):
        mock_geocode.return_value = {'name': 'New York, NY', 'lat': 40.7128, 'lon': -74.0060}
        resp = client.get('/api/geocode/?q=New York')
        assert resp.status_code == 200
        assert resp.json()['name'] == 'New York, NY'

    def test_plan_validation_missing_fields(self, client):
        resp = client.post('/api/plan/', {}, format='json')
        assert resp.status_code == 400
        data = resp.json()
        assert 'error' in data

    def test_plan_validation_invalid_spacing(self, client):
        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            'origin': 'New York, NY',
            'destination': 'Philadelphia, PA',
            'departure': dep,
            'load_lbs': 30000,
            'spacing_miles': 15,  # Only 10, 25, 50 allowed
        }
        resp = client.post('/api/plan/', payload, format='json')
        assert resp.status_code == 400
        data = resp.json()
        assert 'spacing' in str(data).lower()

    def test_plan_validation_excessive_load(self, client):
        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            'origin': 'New York, NY',
            'destination': 'Philadelphia, PA',
            'departure': dep,
            'load_lbs': 120000,  # Max 100,000 lbs
            'spacing_miles': 25,
        }
        resp = client.post('/api/plan/', payload, format='json')
        assert resp.status_code == 400

    def test_plan_validation_departure_past(self, client):
        dep = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        payload = {
            'origin': 'New York, NY',
            'destination': 'Philadelphia, PA',
            'departure': dep,
            'load_lbs': 30000,
            'spacing_miles': 25,
        }
        resp = client.post('/api/plan/', payload, format='json')
        assert resp.status_code == 400

    @patch('routing.views.build_plan')
    def test_plan_endpoint_success(self, mock_build, client):
        mock_build.return_value = {
            'origin': {'name': 'New York, NY', 'lat': 40.71, 'lon': -74.00},
            'destination': {'name': 'Philadelphia, PA', 'lat': 39.95, 'lon': -75.16},
            'departure': '2026-10-18T10:00:00+00:00',
            'load_lbs': 35000,
            'spacing_miles': 25,
            'routes': [],
            'has_safe_route': True,
            'corridor_heatmap': {'frames': []},
            'warning': 'Advisory only.',
        }

        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        payload = {
            'origin': 'New York, NY',
            'destination': 'Philadelphia, PA',
            'departure': dep,
            'load_lbs': 35000,
            'spacing_miles': 25,
        }
        resp = client.post('/api/plan/', payload, format='json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['origin']['name'] == 'New York, NY'
        assert 'corridor_heatmap' in data
