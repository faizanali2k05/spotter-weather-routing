import pytest
from unittest.mock import patch, MagicMock
import requests

from routing.geocoding import geocode_place, GEOCODE_CACHE
from routing.exceptions import LocationNotFoundError


@pytest.fixture(autouse=True)
def clear_geocode_cache():
    GEOCODE_CACHE.clear()
    yield
    GEOCODE_CACHE.clear()


class TestGeocoding:
    @patch('routing.geocoding.requests.Session.get')
    def test_nominatim_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {'display_name': 'New York, NY, USA', 'lat': '40.7128', 'lon': '-74.0060'}
        ]
        mock_get.return_value = mock_resp

        res = geocode_place('New York, NY')
        assert res['name'] == 'New York, NY, USA'
        assert pytest.approx(res['lat'], 0.001) == 40.7128
        assert pytest.approx(res['lon'], 0.001) == -74.0060

    @patch('routing.geocoding.requests.Session.get')
    def test_nominatim_fallback_to_open_meteo_on_403(self, mock_get):
        # 1st call to Nominatim returns 403 Access Denied
        mock_nom = MagicMock()
        mock_nom.status_code = 403

        # 2nd call to Open-Meteo returns 200 with result
        mock_om = MagicMock()
        mock_om.status_code = 200
        mock_om.json.return_value = {
            'results': [
                {'name': 'Philadelphia', 'admin1': 'Pennsylvania', 'country': 'United States', 'latitude': 39.9526, 'longitude': -75.1652}
            ]
        }

        mock_get.side_effect = [mock_nom, mock_om]

        res = geocode_place('Philadelphia, PA')
        assert 'Philadelphia' in res['name']
        assert pytest.approx(res['lat'], 0.001) == 39.9526
        assert pytest.approx(res['lon'], 0.001) == -75.1652

    @patch('routing.geocoding.requests.Session.get')
    def test_nominatim_fallback_on_timeout(self, mock_get):
        mock_om = MagicMock()
        mock_om.status_code = 200
        mock_om.json.return_value = {
            'results': [
                {'name': 'Boston', 'admin1': 'Massachusetts', 'country': 'United States', 'latitude': 42.3601, 'longitude': -71.0589}
            ]
        }

        mock_get.side_effect = [requests.exceptions.Timeout(), mock_om]

        res = geocode_place('Boston, MA')
        assert 'Boston' in res['name']
        assert pytest.approx(res['lat'], 0.001) == 42.3601

    @patch('routing.geocoding.requests.Session.get')
    def test_location_not_found_on_both_providers(self, mock_get):
        mock_nom = MagicMock()
        mock_nom.status_code = 200
        mock_nom.json.return_value = []

        mock_om = MagicMock()
        mock_om.status_code = 200
        mock_om.json.return_value = {'results': []}

        mock_get.side_effect = [mock_nom, mock_om]

        with pytest.raises(LocationNotFoundError):
            geocode_place('NonExistentCityXYZ12345')

    def test_empty_query_raises_not_found(self):
        with pytest.raises(LocationNotFoundError):
            geocode_place('   ')

    @patch('routing.geocoding.requests.Session.get')
    def test_caching_avoids_duplicate_http_calls(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {'display_name': 'Denver, CO, USA', 'lat': '39.7392', 'lon': '-104.9903'}
        ]
        mock_get.return_value = mock_resp

        res1 = geocode_place('Denver, CO')
        res2 = geocode_place('Denver, CO')
        res3 = geocode_place('denver, co')

        assert res1 == res2 == res3
        # Should only call HTTP once because subsequent calls hit in-memory cache
        assert mock_get.call_count == 1

