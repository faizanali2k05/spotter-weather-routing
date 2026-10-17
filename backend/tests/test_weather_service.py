import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from routing.weather_service import (
    interpolate_weather_at_eta,
    fetch_batch_forecasts,
    get_weather_for_checkpoints,
    WEATHER_CACHE,
)
from routing.exceptions import ForecastHorizonError, ProviderRateLimitError, ProviderTimeoutError


@pytest.fixture(autouse=True)
def clear_weather_cache():
    WEATHER_CACHE.clear()
    yield
    WEATHER_CACHE.clear()


class TestWeatherService:
    def test_interpolate_weather_exact_hour(self):
        hourly = {
            'time': ['2026-10-18T10:00', '2026-10-18T11:00', '2026-10-18T12:00'],
            'wind_speed_10m': [20.0, 30.0, 40.0],
            'rain': [0.0, 0.20, 0.50],
            'snowfall': [0.0, 1.0, 2.5],  # Inches direct
        }
        eta = datetime(2026, 10, 18, 11, 0, tzinfo=timezone.utc)
        weather = interpolate_weather_at_eta(hourly, eta)
        assert weather['wind_mph'] == 30.0
        assert weather['rain_inches_hr'] == 0.20
        assert weather['snow_inches_hr'] == 1.0

    def test_interpolate_weather_between_hours(self):
        hourly = {
            'time': ['2026-10-18T10:00', '2026-10-18T11:00'],
            'wind_speed_10m': [20.0, 30.0],
            'rain': [0.10, 0.30],
            'snowfall': [1.0, 2.0],
        }
        # 10:30 is halfway between 10:00 and 11:00
        eta = datetime(2026, 10, 18, 10, 30, tzinfo=timezone.utc)
        weather = interpolate_weather_at_eta(hourly, eta)
        assert weather['wind_mph'] == 25.0
        assert weather['rain_inches_hr'] == 0.20
        assert weather['snow_inches_hr'] == 1.5

    def test_interpolate_weather_horizon_exceeded(self):
        hourly = {
            'time': ['2026-10-18T10:00', '2026-10-18T11:00'],
            'wind_speed_10m': [10.0, 10.0],
            'rain': [0.0, 0.0],
            'snowfall': [0.0, 0.0],
        }
        # 5 days in the future
        eta = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ForecastHorizonError):
            interpolate_weather_at_eta(hourly, eta)

    @patch('routing.weather_service.requests.Session.get')
    def test_batch_forecast_multi_coordinate_request(self, mock_get):
        # Open-Meteo returns a list of items for multiple coordinates
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                'latitude': 40.71,
                'longitude': -74.01,
                'hourly': {
                    'time': ['2026-10-18T10:00'],
                    'wind_speed_10m': [15.0],
                    'rain': [0.05],
                    'snowfall': [0.0],
                }
            },
            {
                'latitude': 39.95,
                'longitude': -75.16,
                'hourly': {
                    'time': ['2026-10-18T10:00'],
                    'wind_speed_10m': [22.0],
                    'rain': [0.12],
                    'snowfall': [0.0],
                }
            }
        ]
        mock_get.return_value = mock_resp

        coords = [(40.71, -74.01), (39.95, -75.16)]
        res = fetch_batch_forecasts(coords)
        assert len(res) == 2
        assert res[(40.71, -74.01)]['wind_speed_10m'] == [15.0]
        assert res[(39.95, -75.16)]['wind_speed_10m'] == [22.0]
        # Verify single HTTP call was made for both coordinates
        assert mock_get.call_count == 1

    @patch('routing.weather_service.requests.Session.get')
    def test_get_weather_for_checkpoints_uses_cache(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                'latitude': 40.71,
                'longitude': -74.01,
                'hourly': {
                    'time': ['2026-10-18T10:00'],
                    'wind_speed_10m': [18.0],
                    'rain': [0.0],
                    'snowfall': [0.0],
                }
            }
        ]
        mock_get.return_value = mock_resp

        pts = [{'lat': 40.712, 'lon': -74.006}]
        etas = [datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)]

        # Call 1: fetches from HTTP
        out1 = get_weather_for_checkpoints(pts, etas)
        assert out1[0]['wind_mph'] == 18.0
        assert mock_get.call_count == 1

        # Call 2: identical coordinate hits cache
        out2 = get_weather_for_checkpoints(pts, etas)
        assert out2[0]['wind_mph'] == 18.0
        assert mock_get.call_count == 1  # No second call

