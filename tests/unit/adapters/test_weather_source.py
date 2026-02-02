"""
Tests for Weather Data Sources.

Tests both mock and real weather provider implementations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from omen.adapters.inbound.weather.openweather_client import (
    OpenWeatherClient,
    OpenWeatherAlert,
    OpenWeatherResponse,
)
from omen.adapters.inbound.weather.source import (
    WeatherSignalSource,
    MockWeatherSignalSource,
)
from omen.adapters.inbound.weather.schemas import (
    StormAlert,
    WeatherWarning,
    SeaConditions,
)


class TestOpenWeatherClient:
    """Tests for OpenWeatherMap client."""
    
    def test_client_not_configured_without_api_key(self):
        """Client should report not configured without API key."""
        with patch.dict("os.environ", {}, clear=True):
            client = OpenWeatherClient(api_key=None)
            assert client.is_configured is False
    
    def test_client_configured_with_api_key(self):
        """Client should report configured with API key."""
        client = OpenWeatherClient(api_key="test_api_key")
        assert client.is_configured is True
    
    def test_monitored_locations_defined(self):
        """Monitored locations should include major logistics hubs."""
        client = OpenWeatherClient(api_key="test")
        
        # Major ports should be monitored
        assert "singapore" in client.MONITORED_LOCATIONS
        assert "shanghai" in client.MONITORED_LOCATIONS
        assert "rotterdam" in client.MONITORED_LOCATIONS
        assert "los_angeles" in client.MONITORED_LOCATIONS
        
        # Vietnam ports should be monitored (partner relevance)
        assert "ho_chi_minh" in client.MONITORED_LOCATIONS
        assert "hai_phong" in client.MONITORED_LOCATIONS
    
    def test_logistics_relevant_events_defined(self):
        """Logistics-relevant event types should be defined."""
        client = OpenWeatherClient(api_key="test")
        
        assert "typhoon" in client.LOGISTICS_RELEVANT_EVENTS
        assert "hurricane" in client.LOGISTICS_RELEVANT_EVENTS
        assert "flood" in client.LOGISTICS_RELEVANT_EVENTS
        assert "fog" in client.LOGISTICS_RELEVANT_EVENTS
    
    def test_is_logistics_relevant_typhoon(self):
        """Typhoon should be identified as logistics relevant."""
        client = OpenWeatherClient(api_key="test")
        
        alert = OpenWeatherAlert(
            sender_name="JTWC",
            event="Typhoon Warning",
            start=1704067200,
            end=1704153600,
            description="Typhoon approaching",
        )
        
        assert client._is_logistics_relevant(alert) is True
    
    def test_is_logistics_relevant_fog(self):
        """Fog should be identified as logistics relevant."""
        client = OpenWeatherClient(api_key="test")
        
        alert = OpenWeatherAlert(
            sender_name="NWS",
            event="Dense Fog Advisory",
            start=1704067200,
            end=1704153600,
            description="Dense fog expected",
        )
        
        assert client._is_logistics_relevant(alert) is True
    
    def test_is_logistics_relevant_irrelevant(self):
        """Non-logistics events should be filtered out."""
        client = OpenWeatherClient(api_key="test")
        
        alert = OpenWeatherAlert(
            sender_name="NWS",
            event="Heat Advisory",
            start=1704067200,
            end=1704153600,
            description="Hot weather expected",
        )
        
        assert client._is_logistics_relevant(alert) is False
    
    def test_calculate_probability_hurricane(self):
        """Hurricane should have high probability."""
        client = OpenWeatherClient(api_key="test")
        
        alert = OpenWeatherAlert(
            sender_name="NHC",
            event="Hurricane Warning",
            start=1704067200,
            end=1704153600,
            description="Hurricane approaching",
        )
        
        prob = client._calculate_probability(alert)
        assert prob >= 0.9  # High probability for hurricanes
    
    def test_calculate_probability_fog(self):
        """Fog should have moderate probability."""
        client = OpenWeatherClient(api_key="test")
        
        alert = OpenWeatherAlert(
            sender_name="NWS",
            event="Dense Fog Advisory",
            start=1704067200,
            end=1704153600,
            description="Dense fog expected",
        )
        
        prob = client._calculate_probability(alert)
        assert 0.5 <= prob <= 0.8
    
    @pytest.mark.asyncio
    async def test_fetch_all_alerts_empty_when_not_configured(self):
        """fetch_all_alerts should return empty when not configured."""
        client = OpenWeatherClient(api_key=None)
        
        events = await client.fetch_all_alerts()
        
        assert events == []
    
    @pytest.mark.asyncio
    async def test_health_check_unconfigured(self):
        """Health check should report unconfigured status."""
        from omen.application.ports.health_checkable import HealthStatus
        
        client = OpenWeatherClient(api_key=None)
        
        health = await client.health_check()
        
        # health is a HealthCheckResult object, not a dict
        assert health.status == HealthStatus.UNKNOWN
        assert health.error_message is not None, "Expected error message for unconfigured client"
        assert "not configured" in health.error_message.lower()


class TestWeatherSignalSource:
    """Tests for Weather Signal Source."""
    
    def test_source_name(self):
        """Source name should be 'weather'."""
        source = WeatherSignalSource()
        assert source.source_name == "weather"
    
    def test_fetch_events_returns_iterator(self):
        """fetch_events should return an iterator."""
        source = WeatherSignalSource()
        
        events = source.fetch_events(limit=10)
        
        # Should be iterable
        event_list = list(events)
        assert isinstance(event_list, list)
    
    @pytest.mark.asyncio
    async def test_fetch_events_async_returns_async_iterator(self):
        """fetch_events_async should return async iterator."""
        source = WeatherSignalSource()
        
        events = []
        async for event in source.fetch_events_async(limit=10):
            events.append(event)
        
        assert isinstance(events, list)


class TestMockWeatherSignalSource:
    """Tests for Mock Weather Signal Source."""
    
    def test_normal_scenario_no_storms(self):
        """Normal scenario should have no storms."""
        source = MockWeatherSignalSource(scenario="normal")
        
        storms = source._generate_mock_storms()
        
        assert storms == []
    
    def test_typhoon_scenario_has_storm(self):
        """Typhoon scenario should have a storm."""
        source = MockWeatherSignalSource(scenario="typhoon")
        
        storms = source._generate_mock_storms()
        
        assert len(storms) == 1
        assert storms[0].storm_type == "typhoon"
        assert storms[0].name == "Haiyan"
    
    def test_hurricane_scenario_has_storm(self):
        """Hurricane scenario should have a storm."""
        source = MockWeatherSignalSource(scenario="hurricane")
        
        storms = source._generate_mock_storms()
        
        assert len(storms) == 1
        assert storms[0].storm_type == "hurricane"


class TestStormAlert:
    """Tests for StormAlert schema."""
    
    def test_storm_alert_creation(self):
        """StormAlert should be created with valid data."""
        now = datetime.now(timezone.utc)
        
        storm = StormAlert(
            storm_id="WP202601",
            name="Haiyan",
            storm_type="typhoon",
            category=4,
            lat=15.5,
            lon=130.2,
            wind_speed_kts=130,
            pressure_mb=935,
            path_confidence=0.8,
            affected_shipping_lanes=["Trans-Pacific"],
            affected_ports=["HKHKG", "CNSHA"],
            estimated_vessels_at_risk=60,
            timestamp=now,
        )
        
        assert storm.storm_id == "WP202601"
        assert storm.category == 4
        assert 0 <= storm.path_confidence <= 1
    
    def test_storm_alert_category_bounds(self):
        """Storm category should be bounded 0-5."""
        now = datetime.now(timezone.utc)
        
        # Valid category
        storm = StormAlert(
            storm_id="test",
            name="Test",
            storm_type="hurricane",
            category=3,
            lat=0,
            lon=0,
            wind_speed_kts=100,
            pressure_mb=960,
            timestamp=now,
        )
        assert storm.category == 3
        
        # Invalid category should raise
        with pytest.raises(Exception):  # ValidationError
            StormAlert(
                storm_id="test",
                name="Test",
                storm_type="hurricane",
                category=6,  # Invalid: > 5
                lat=0,
                lon=0,
                wind_speed_kts=100,
                pressure_mb=960,
                timestamp=now,
            )


class TestWeatherWarning:
    """Tests for WeatherWarning schema."""
    
    def test_weather_warning_creation(self):
        """WeatherWarning should be created with valid data."""
        now = datetime.now(timezone.utc)
        
        warning = WeatherWarning(
            warning_id="WW20260101",
            warning_type="gale",
            severity="warning",
            region="South China Sea",
            headline="Gale Warning",
            start_time=now,
            timestamp=now,
        )
        
        assert warning.warning_id == "WW20260101"
        assert warning.severity == "warning"
    
    def test_weather_warning_severity_levels(self):
        """Warning severity should be one of defined levels."""
        from typing import Literal, get_args
        now = datetime.now(timezone.utc)
        
        # Use Literal type for severity to match schema
        SeverityType = Literal["advisory", "watch", "warning", "emergency"]
        severity_values: tuple[SeverityType, ...] = get_args(SeverityType)
        
        for severity in severity_values:
            warning = WeatherWarning(
                warning_id="test",
                warning_type="storm",
                severity=severity,
                region="Test",
                headline="Test",
                start_time=now,
                timestamp=now,
            )
            assert warning.severity == severity


class TestSeaConditions:
    """Tests for SeaConditions schema."""
    
    def test_sea_conditions_creation(self):
        """SeaConditions should be created with valid data."""
        now = datetime.now(timezone.utc)
        
        conditions = SeaConditions(
            region="South China Sea",
            wave_height_m=3.5,
            wind_speed_kts=25,
            sea_state=5,
            conditions="rough",
            timestamp=now,
        )
        
        assert conditions.wave_height_m == 3.5
        assert conditions.conditions == "rough"
    
    def test_sea_state_bounds(self):
        """Sea state should be bounded 0-9 (Douglas scale)."""
        now = datetime.now(timezone.utc)
        
        # Valid sea state
        conditions = SeaConditions(
            region="Test",
            wave_height_m=3.5,
            wind_speed_kts=25,
            sea_state=7,
            conditions="very_rough",
            timestamp=now,
        )
        assert conditions.sea_state == 7
        
        # Invalid sea state should raise
        with pytest.raises(Exception):  # ValidationError
            SeaConditions(
                region="Test",
                wave_height_m=3.5,
                wind_speed_kts=25,
                sea_state=10,  # Invalid: > 9
                conditions="phenomenal",
                timestamp=now,
            )
