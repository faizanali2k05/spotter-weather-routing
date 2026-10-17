import pytest
from routing.services import route_checkpoints, haversine_miles


class TestCheckpoints:
    def test_haversine_distance_accuracy(self):
        # Known distance between NYC (40.7128, -74.0060) and Philadelphia (39.9526, -75.1652) is ~80.5 miles as the crow flies
        d = haversine_miles([-74.0060, 40.7128], [-75.1652, 39.9526])
        assert 80.0 <= d <= 82.0

    def test_resample_checkpoints_spacing_25_miles(self):
        # Straight line of ~100 miles
        # Each degree latitude is ~69 miles
        start = [-74.0, 40.0]
        end = [-74.0, 41.45]  # ~100 miles north
        coords = [start, end]
        duration_seconds = 7200  # 2 hours

        checkpoints = route_checkpoints(coords, duration_seconds, spacing_miles=25)

        # Should include: mile 0, mile 25, mile 50, mile 75, and mile ~100
        assert len(checkpoints) >= 5
        assert checkpoints[0]['mile'] == 0.0
        assert checkpoints[0]['offset_seconds'] == 0
        assert checkpoints[1]['mile'] == 25.0
        assert checkpoints[-1]['mile'] == pytest.approx(100.0, abs=2.0)
        assert checkpoints[-1]['offset_seconds'] == duration_seconds

    def test_resample_checkpoints_spacing_10_miles(self):
        start = [-74.0, 40.0]
        end = [-74.0, 40.5]  # ~34.5 miles
        coords = [start, end]
        duration_seconds = 3600

        checkpoints = route_checkpoints(coords, duration_seconds, spacing_miles=10)
        # Should include: 0, 10, 20, 30, and total ~34.5
        assert len(checkpoints) == 5
        assert checkpoints[0]['mile'] == 0.0
        assert checkpoints[1]['mile'] == 10.0
        assert checkpoints[2]['mile'] == 20.0
        assert checkpoints[3]['mile'] == 30.0

    def test_resample_single_point(self):
        checkpoints = route_checkpoints([[-74.0, 40.0]], 0, 25)
        assert len(checkpoints) == 1
        assert checkpoints[0]['mile'] == 0.0

