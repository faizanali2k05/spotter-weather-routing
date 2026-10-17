import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from routing.weather_service import (
    fetch_batch_forecasts,
    get_weather_for_checkpoints,
    WEATHER_CACHE,
)
from routing.services import build_plan
from routing.corridor_service import build_corridor_heatmap
from routing.exceptions import ProviderRateLimitError


@pytest.fixture(autouse=True)
def clear_weather_cache():
    WEATHER_CACHE.clear()
    yield
    WEATHER_CACHE.clear()


def make_mock_hourly():
    return {
        'time': [f'2026-10-18T{h:02d}:00' for h in range(48)],
        'wind_speed_10m': [15.0] * 48,
        'rain': [0.0] * 48,
        'snowfall': [0.0] * 48,
    }


class TestWeatherCachingAndResilience:
    @patch('time.sleep')
    @patch('routing.weather_service.requests.Session.get')
    def test_fetch_batch_forecasts_retries_on_429_and_succeeds(self, mock_get, mock_sleep):
        # First attempt: 429 with Retry-After header
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {'Retry-After': '1'}
        resp_429.json.return_value = {'reason': 'Minutely rate limit reached'}

        # Second attempt: 200 OK
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = [
            {
                'latitude': 40.71,
                'longitude': -74.01,
                'hourly': make_mock_hourly(),
            }
        ]

        mock_get.side_effect = [resp_429, resp_200]

        result = fetch_batch_forecasts([(40.71, -74.01)])
        assert (40.71, -74.01) in result
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch('time.sleep')
    @patch('routing.weather_service.requests.Session.get')
    def test_fetch_batch_forecasts_raises_when_429_retries_exhausted(self, mock_get, mock_sleep):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {}
        resp_429.json.return_value = {'reason': 'Hourly limit of 5000 requests exceeded'}

        mock_get.return_value = resp_429

        with pytest.raises(ProviderRateLimitError) as exc_info:
            fetch_batch_forecasts([(40.71, -74.01)])

        assert 'Hourly limit of 5000 requests exceeded' in str(exc_info.value)
        # 1 initial + 2 retries = 3 calls total
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    def test_prefetched_forecasts_avoids_extra_http_calls(self):
        pts = [{'lat': 40.712, 'lon': -74.006, 'mile': 0.0, 'offset_seconds': 0}]
        etas = [datetime(2026, 10, 18, 10, 0, tzinfo=timezone.utc)]
        mock_hourly = make_mock_hourly()

        prefetched = {(40.71, -74.01): mock_hourly}

        with patch('routing.weather_service.fetch_batch_forecasts') as mock_fetch:
            weather = get_weather_for_checkpoints(pts, etas, prefetched_forecasts=prefetched)
            assert len(weather) == 1
            assert weather[0]['wind_mph'] == 15.0
            # fetch_batch_forecasts should NOT have been called because coordinate was prefetched
            mock_fetch.assert_not_called()

    @patch('routing.services.geocode_place')
    @patch('routing.services.get_routing_provider')
    @patch('routing.services.fetch_batch_forecasts')
    def test_build_plan_single_batch_forecast_call(self, mock_fetch, mock_provider, mock_geocode):
        # 2 alternative routes sharing origin and destination
        mock_geocode.side_effect = [
            {'name': 'New York, NY', 'lat': 40.7128, 'lon': -74.0060},
            {'name': 'Philadelphia, PA', 'lat': 39.9526, 'lon': -75.1652},
        ]

        provider_inst = MagicMock()
        provider_inst.get_routes.return_value = [
            {
                'geometry': [[-74.0060, 40.7128], [-74.5, 40.3], [-75.1652, 39.9526]],
                'duration_seconds': 7200,
                'distance_meters': 150000,
            },
            {
                'geometry': [[-74.0060, 40.7128], [-74.7, 40.1], [-75.1652, 39.9526]],
                'duration_seconds': 7500,
                'distance_meters': 155000,
            },
        ]
        mock_provider.return_value = provider_inst

        # Mock fetch_batch_forecasts returning valid hourly data for all requested points
        def fake_fetch(coords, session=None):
            return {c: make_mock_hourly() for c in coords}

        mock_fetch.side_effect = fake_fetch

        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        plan = build_plan(
            origin_text='New York, NY',
            destination_text='Philadelphia, PA',
            departure_str=dep,
            load_lbs=35000,
            spacing_miles=25,
        )

        assert len(plan['routes']) == 2
        # All coordinates for both routes and corridor heatmap were requested in 1 single batch call
        assert mock_fetch.call_count == 1
        assert plan['corridor_heatmap'] is not None
        assert plan['corridor_heatmap']['corridor_stations_count'] > 0

    @patch('routing.services.geocode_place')
    @patch('routing.services.get_routing_provider')
    @patch('routing.services.fetch_batch_forecasts')
    @patch('routing.services.build_corridor_heatmap')
    def test_build_plan_succeeds_when_heatmap_fails_with_rate_limit(
        self, mock_build_heatmap, mock_fetch, mock_provider, mock_geocode
    ):
        mock_geocode.side_effect = [
            {'name': 'New York, NY', 'lat': 40.7128, 'lon': -74.0060},
            {'name': 'Philadelphia, PA', 'lat': 39.9526, 'lon': -75.1652},
        ]

        provider_inst = MagicMock()
        provider_inst.get_routes.return_value = [
            {
                'geometry': [[-74.0060, 40.7128], [-75.1652, 39.9526]],
                'duration_seconds': 5400,
                'distance_meters': 150000,
            }
        ]
        mock_provider.return_value = provider_inst

        mock_fetch.side_effect = lambda coords, session=None: {c: make_mock_hourly() for c in coords}

        # Heatmap raises rate limit error
        mock_build_heatmap.side_effect = ProviderRateLimitError("Open-Meteo 429 during heatmap generation")

        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        plan = build_plan(
            origin_text='New York, NY',
            destination_text='Philadelphia, PA',
            departure_str=dep,
            load_lbs=35000,
            spacing_miles=25,
        )

        # Route analysis must succeed completely
        assert len(plan['routes']) == 1
        route = plan['routes'][0]
        assert len(route['checkpoints']) > 0
        assert route['summary'] is not None
        assert route['recommended'] is True

        # Heatmap gracefully reports 0 stations and empty frames
        assert plan['corridor_heatmap']['corridor_stations_count'] == 0
        assert plan['corridor_heatmap']['frames'] == []
        assert 'heatmap overlay is currently unavailable due to weather provider limits' in plan['warning']

    @patch('routing.services.geocode_place')
    @patch('routing.services.get_routing_provider')
    @patch('routing.services.fetch_batch_forecasts')
    def test_build_plan_falls_back_when_combined_batch_rate_limited(
        self, mock_fetch, mock_provider, mock_geocode
    ):
        mock_geocode.side_effect = [
            {'name': 'New York, NY', 'lat': 40.7128, 'lon': -74.0060},
            {'name': 'Philadelphia, PA', 'lat': 39.9526, 'lon': -75.1652},
        ]

        provider_inst = MagicMock()
        provider_inst.get_routes.return_value = [
            {
                'geometry': [[-74.0060, 40.7128], [-75.1652, 39.9526]],
                'duration_seconds': 5400,
                'distance_meters': 150000,
            }
        ]
        mock_provider.return_value = provider_inst

        # First call (combined coordinates) fails with 429
        # Second call (essential route coordinates only) succeeds
        def side_effect_fetch(coords, session=None):
            if len(coords) > 5:
                raise ProviderRateLimitError("Combined coordinate limit reached")
            return {c: make_mock_hourly() for c in coords}

        mock_fetch.side_effect = side_effect_fetch

        dep = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        plan = build_plan(
            origin_text='New York, NY',
            destination_text='Philadelphia, PA',
            departure_str=dep,
            load_lbs=35000,
            spacing_miles=25,
        )

        assert len(plan['routes']) == 1
        assert len(plan['routes'][0]['checkpoints']) > 0
