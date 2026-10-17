import pytest
from routing.risk import (
    classify,
    classify_detailed,
    classify_wind,
    classify_rain,
    classify_snow,
    summarize,
    ranking_key,
    build_recommendation_reason,
    LEVELS,
)


class TestRiskThresholds:
    def test_wind_threshold_boundaries(self):
        # Low: < 25
        assert classify_wind(0.0, 0)[0] == 0
        assert classify_wind(24.9, 0)[0] == 0

        # Moderate: 25 to < 35
        assert classify_wind(25.0, 0)[0] == 1
        assert classify_wind(34.9, 0)[0] == 1

        # High: 35 to < 45
        assert classify_wind(35.0, 0)[0] == 2
        assert classify_wind(44.9, 0)[0] == 2

        # Severe: 45 to < 55
        assert classify_wind(45.0, 0)[0] == 3
        assert classify_wind(54.9, 0)[0] == 3

        # No Travel: 55+
        assert classify_wind(55.0, 0)[0] == 4
        assert classify_wind(75.0, 0)[0] == 4

    def test_rain_threshold_boundaries(self):
        # Low: < 0.10
        assert classify_rain(0.0)[0] == 0
        assert classify_rain(0.099)[0] == 0

        # Moderate: 0.10 to < 0.25
        assert classify_rain(0.10)[0] == 1
        assert classify_rain(0.249)[0] == 1

        # High: 0.25 to < 0.50
        assert classify_rain(0.25)[0] == 2
        assert classify_rain(0.499)[0] == 2

        # Severe: 0.50 to 1.00 (inclusive)
        assert classify_rain(0.50)[0] == 3
        assert classify_rain(1.00)[0] == 3

        # No Travel: > 1.00
        assert classify_rain(1.001)[0] == 4
        assert classify_rain(2.50)[0] == 4

    def test_snow_threshold_boundaries(self):
        # Low: < 0.5
        assert classify_snow(0.0)[0] == 0
        assert classify_snow(0.49)[0] == 0

        # Moderate: 0.5 to < 1.0
        assert classify_snow(0.50)[0] == 1
        assert classify_snow(0.99)[0] == 1

        # High: 1.0 to < 2.0
        assert classify_snow(1.00)[0] == 2
        assert classify_snow(1.99)[0] == 2

        # Severe: 2.0 to 3.0 (inclusive)
        assert classify_snow(2.00)[0] == 3
        assert classify_snow(3.00)[0] == 3

        # No Travel: > 3.0
        assert classify_snow(3.01)[0] == 4
        assert classify_snow(5.00)[0] == 4

    def test_load_dependent_wind_rules(self):
        # Wind 45–54 mph and load > 30,000 lb => No Travel (level 4)
        lvl_under, factors_under = classify_wind(48.0, 30000)
        assert lvl_under == 3  # Severe
        lvl_over, factors_over = classify_wind(48.0, 30001)
        assert lvl_over == 4  # No Travel
        assert any("No Travel" in f for f in factors_over)

        # Wind 35–44 mph and load > 40,000 lb => Severe (level 3)
        lvl_load_under, _ = classify_wind(38.0, 40000)
        assert lvl_load_under == 2  # High
        lvl_load_over, factors_load_over = classify_wind(38.0, 40001)
        assert lvl_load_over == 3  # Severe
        assert any("Severe" in f for f in factors_load_over)

    def test_multi_hazard_combination(self):
        # Extreme rain dominates over low wind
        level, factors = classify_detailed(15.0, 1.2, 0.0, 20000)
        assert level == 'No Travel'
        assert any("rainfall" in f.lower() for f in factors)

        # High snow dominates over moderate rain
        level, factors = classify_detailed(10.0, 0.15, 1.5, 20000)
        assert level == 'High'
        assert any("snow" in f.lower() for f in factors)


class TestSummarizeAndRanking:
    def test_summarize_mileage_distribution(self):
        checkpoints = [
            {'mile': 0.0, 'risk': 'Low', 'factors': []},
            {'mile': 50.0, 'risk': 'Severe', 'factors': ['Severe wind']},
            {'mile': 100.0, 'risk': 'Low', 'factors': []},
        ]
        summary = summarize(checkpoints, 100.0)
        assert summary['miles_by_risk']['Low'] == 50.0
        assert summary['miles_by_risk']['Severe'] == 50.0
        assert summary['miles_by_risk']['No Travel'] == 0.0
        assert summary['worst_severity'] == 'Severe'
        assert summary['no_travel'] is False
        assert 'Severe wind' in summary['dominant_hazards']

    def test_summarize_no_travel_flag(self):
        checkpoints = [
            {'mile': 0.0, 'risk': 'Low', 'factors': []},
            {'mile': 25.0, 'risk': 'No Travel', 'factors': ['Extreme wind']},
            {'mile': 50.0, 'risk': 'Low', 'factors': []},
        ]
        summary = summarize(checkpoints, 50.0)
        assert summary['no_travel'] is True
        assert summary['worst_severity'] == 'No Travel'

    def test_ranking_prefers_safe_over_no_travel(self):
        safe_route = {
            'id': 1,
            'duration_minutes': 120,
            'distance_miles': 100.0,
            'summary': {
                'no_travel': False,
                'miles_by_risk': {'Low': 80.0, 'Moderate': 15.0, 'High': 5.0, 'Severe': 0.0, 'No Travel': 0.0},
                'average_risk': 0.25,
            }
        }
        no_travel_route = {
            'id': 2,
            'duration_minutes': 90,  # faster, but dangerous!
            'distance_miles': 80.0,
            'summary': {
                'no_travel': True,
                'miles_by_risk': {'Low': 60.0, 'Moderate': 0.0, 'High': 0.0, 'Severe': 0.0, 'No Travel': 20.0},
                'average_risk': 1.0,
            }
        }

        routes = [no_travel_route, safe_route]
        routes.sort(key=ranking_key)
        assert routes[0]['id'] == 1  # Safe route must rank first despite longer duration

    def test_ranking_prefers_lower_severe_exposure(self):
        route_a = {
            'id': 1,
            'duration_minutes': 100,
            'distance_miles': 100.0,
            'summary': {
                'no_travel': False,
                'miles_by_risk': {'Low': 70.0, 'Moderate': 10.0, 'High': 20.0, 'Severe': 0.0, 'No Travel': 0.0},
                'average_risk': 0.5,
            }
        }
        route_b = {
            'id': 2,
            'duration_minutes': 95,
            'distance_miles': 95.0,
            'summary': {
                'no_travel': False,
                'miles_by_risk': {'Low': 80.0, 'Moderate': 0.0, 'High': 0.0, 'Severe': 15.0, 'No Travel': 0.0},
                'average_risk': 0.5,
            }
        }

        routes = [route_b, route_a]
        routes.sort(key=ranking_key)
        assert routes[0]['id'] == 1  # route_a has 0 Severe miles vs route_b with 15

    def test_recommendation_reason_generation(self):
        route = {
            'id': 1,
            'distance_miles': 150.0,
            'summary': {
                'no_travel': False,
                'miles_by_risk': {'Low': 150.0, 'Moderate': 0.0, 'High': 0.0, 'Severe': 0.0, 'No Travel': 0.0},
                'dominant_hazards': [],
            }
        }
        reason = build_recommendation_reason(route, [route])
        assert "optimal conditions" in reason.lower()

        unsafe_route = {
            'id': 2,
            'distance_miles': 150.0,
            'summary': {
                'no_travel': True,
                'miles_by_risk': {'Low': 100.0, 'Moderate': 0.0, 'High': 0.0, 'Severe': 0.0, 'No Travel': 50.0},
                'dominant_hazards': ['Extreme wind (58 mph)'],
            }
        }
        unsafe_reason = build_recommendation_reason(unsafe_route, [unsafe_route])
        assert "not recommended" in unsafe_reason.lower()
        assert "postpone" in unsafe_reason.lower()
