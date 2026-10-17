import os
import pytest
from datetime import datetime, timezone, timedelta
from routing.services import build_plan

RUN_LIVE = os.getenv('RUN_LIVE_TESTS', '0') == '1'


@pytest.mark.skipif(not RUN_LIVE, reason="Live external integration tests disabled by default. Set RUN_LIVE_TESTS=1 to run.")
class TestLiveExternalProvidersSmoke:
    def test_live_route_planning_nyc_to_philly(self):
        dep = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        plan = build_plan(
            origin_text='New York, NY',
            destination_text='Philadelphia, PA',
            departure_str=dep,
            load_lbs=35000,
            spacing_miles=25,
        )
        assert plan['origin']['lat'] > 40.0
        assert plan['destination']['lat'] < 40.5
        assert len(plan['routes']) >= 1
        assert 'corridor_heatmap' in plan
        assert len(plan['corridor_heatmap']['frames']) > 0
