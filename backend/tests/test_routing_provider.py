import pytest
from unittest.mock import patch, MagicMock
import requests

from routing.routing_provider import OSRMProvider, deduplicate_routes, CommercialTruckRoutingProviderAdapter
from routing.exceptions import RouteNotFoundError, ProviderTimeoutError, ProviderRateLimitError, MalformedProviderResponseError


class TestRoutingProvider:
    def test_deduplicate_routes(self):
        # Two routes with nearly identical distances and durations
        r1 = {
            'distance': 100000.0,
            'duration': 5000.0,
            'geometry': {'coordinates': [[-74.0, 40.7], [-74.5, 40.3], [-75.1, 39.9]]}
        }
        r2 = {
            'distance': 100200.0,  # 0.2% diff
            'duration': 5010.0,    # 0.2% diff
            'geometry': {'coordinates': [[-74.0, 40.7], [-74.51, 40.31], [-75.1, 39.9]]}
        }
        # A distinctly different alternative route
        r3 = {
            'distance': 120000.0,  # 20% diff
            'duration': 6500.0,
            'geometry': {'coordinates': [[-74.0, 40.7], [-74.2, 41.0], [-75.1, 39.9]]}
        }

        deduped = deduplicate_routes([r1, r2, r3])
        assert len(deduped) == 2
        assert deduped[0] == r1
        assert deduped[1] == r3

    @patch('routing.routing_provider.requests.Session.get')
    def test_osrm_provider_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'code': 'Ok',
            'routes': [
                {
                    'distance': 150000.0,
                    'duration': 7200.0,
                    'geometry': {'coordinates': [[-74.0, 40.7], [-75.1, 39.9]]}
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = OSRMProvider()
        origin = {'name': 'Origin', 'lat': 40.7, 'lon': -74.0}
        dest = {'name': 'Destination', 'lat': 39.9, 'lon': -75.1}

        routes = provider.get_routes(origin, dest)
        assert len(routes) == 1
        assert routes[0]['distance_meters'] == 150000.0
        assert routes[0]['duration_seconds'] == 7200.0
        assert len(routes[0]['geometry']) == 2

    @patch('routing.routing_provider.requests.Session.get')
    def test_osrm_no_route_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'code': 'NoRoute',
            'routes': []
        }
        mock_get.return_value = mock_resp

        provider = OSRMProvider()
        with pytest.raises(RouteNotFoundError):
            provider.get_routes({'name': 'Island', 'lat': 0.0, 'lon': 0.0}, {'name': 'Mainland', 'lat': 10.0, 'lon': 10.0})

    @patch('routing.routing_provider.requests.Session.get')
    def test_osrm_rate_limit(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        provider = OSRMProvider()
        with pytest.raises(ProviderRateLimitError):
            provider.get_routes({'name': 'A', 'lat': 40.0, 'lon': -74.0}, {'name': 'B', 'lat': 41.0, 'lon': -75.0})

    @patch('routing.routing_provider.requests.Session.get')
    def test_osrm_timeout_raises_provider_timeout_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        provider = OSRMProvider()
        with pytest.raises(ProviderTimeoutError):
            provider.get_routes({'name': 'A', 'lat': 40.0, 'lon': -74.0}, {'name': 'B', 'lat': 41.0, 'lon': -75.0})

    def test_truck_adapter_without_key_falls_back_or_documents(self):
        fallback = MagicMock()
        fallback.get_routes.return_value = [{'distance_meters': 100, 'duration_seconds': 50, 'geometry': [[0, 0], [1, 1]]}]
        adapter = CommercialTruckRoutingProviderAdapter(api_key=None, fallback_provider=fallback)
        assert adapter.is_truck_specific is False
        res = adapter.get_routes({'name': 'A'}, {'name': 'B'})
        assert len(res) == 1
        assert fallback.get_routes.called

