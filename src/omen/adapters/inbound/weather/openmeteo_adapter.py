"""
Open-Meteo Weather Adapter
FREE API - NO API KEY REQUIRED
https://open-meteo.com
"""

import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data for a location."""
    location: str
    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float
    wind_direction: int
    precipitation_mm: float
    weather_code: int
    humidity: Optional[float]
    timestamp: datetime
    
    @property
    def weather_description(self) -> str:
        """Convert WMO weather code to description."""
        codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
            82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
        }
        return codes.get(self.weather_code, "Unknown")
    
    @property
    def is_severe(self) -> bool:
        """Check if weather conditions are severe (impacts shipping)."""
        return (
            self.weather_code >= 65 or
            self.wind_speed_kmh > 50 or
            self.weather_code >= 95
        )
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['weather_description'] = self.weather_description
        data['is_severe'] = self.is_severe
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MarineWeather:
    """Marine weather data for shipping routes."""
    latitude: float
    longitude: float
    wave_height_m: float
    wave_direction: int
    wave_period_s: float
    wind_wave_height_m: float
    swell_height_m: float
    swell_direction: int
    timestamp: datetime
    
    @property
    def is_dangerous(self) -> bool:
        """Check if marine conditions are dangerous for shipping."""
        return self.wave_height_m > 4.0 or self.swell_height_m > 5.0


class OpenMeteoAdapter:
    """
    Open-Meteo Weather API Adapter.
    
    Features:
    - NO API KEY REQUIRED
    - 10,000 calls/day free tier
    - Global coverage 1-11km resolution
    - Marine forecasts for shipping routes
    """
    
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
    
    MAJOR_PORTS = {
        "singapore": {"lat": 1.29, "lon": 103.85, "name": "Singapore"},
        "shanghai": {"lat": 31.23, "lon": 121.47, "name": "Shanghai"},
        "rotterdam": {"lat": 51.92, "lon": 4.48, "name": "Rotterdam"},
        "los_angeles": {"lat": 33.74, "lon": -118.27, "name": "Los Angeles"},
        "hong_kong": {"lat": 22.32, "lon": 114.17, "name": "Hong Kong"},
        "busan": {"lat": 35.10, "lon": 129.04, "name": "Busan"},
        "ho_chi_minh": {"lat": 10.82, "lon": 106.63, "name": "Ho Chi Minh City"},
        "hai_phong": {"lat": 20.86, "lon": 106.68, "name": "Hai Phong"},
        "da_nang": {"lat": 16.07, "lon": 108.22, "name": "Da Nang"},
        "dubai": {"lat": 25.27, "lon": 55.29, "name": "Dubai"},
    }
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={"User-Agent": "OMEN/1.0"}
        )
        logger.info("OpenMeteoAdapter initialized (no API key required)")
    
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        location_name: str = "Unknown"
    ) -> WeatherData:
        """Get current weather for a location."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m"
            ],
            "timezone": "auto"
        }
        
        try:
            response = await self.client.get(self.FORECAST_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            
            return WeatherData(
                location=location_name,
                latitude=latitude,
                longitude=longitude,
                temperature_c=current.get("temperature_2m", 0),
                wind_speed_kmh=current.get("wind_speed_10m", 0),
                wind_direction=current.get("wind_direction_10m", 0),
                precipitation_mm=current.get("precipitation", 0),
                weather_code=current.get("weather_code", 0),
                humidity=current.get("relative_humidity_2m"),
                timestamp=datetime.fromisoformat(
                    current.get("time", datetime.utcnow().isoformat())
                )
            )
        except httpx.HTTPError as e:
            logger.error(f"OpenMeteo API error: {e}")
            raise
    
    async def get_port_weather(self, port_key: str) -> WeatherData:
        """Get weather for a specific port."""
        if port_key not in self.MAJOR_PORTS:
            raise ValueError(f"Unknown port: {port_key}")
        
        port = self.MAJOR_PORTS[port_key]
        return await self.get_current_weather(
            latitude=port["lat"],
            longitude=port["lon"],
            location_name=port["name"]
        )
    
    async def get_all_ports_weather(self) -> Dict[str, WeatherData]:
        """Get weather for all major ports."""
        results = {}
        for port_key in self.MAJOR_PORTS:
            try:
                results[port_key] = await self.get_port_weather(port_key)
            except Exception as e:
                logger.warning(f"Failed to get weather for {port_key}: {e}")
        return results
    
    async def get_marine_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3
    ) -> List[MarineWeather]:
        """Get marine forecast for shipping route analysis."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": [
                "wave_height",
                "wave_direction",
                "wave_period",
                "wind_wave_height",
                "swell_wave_height",
                "swell_wave_direction"
            ],
            "forecast_days": min(days, 7)
        }
        
        try:
            response = await self.client.get(self.MARINE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            results = []
            for i, time_str in enumerate(times[:24]):
                results.append(MarineWeather(
                    latitude=latitude,
                    longitude=longitude,
                    wave_height_m=hourly.get("wave_height", [0])[i] or 0,
                    wave_direction=hourly.get("wave_direction", [0])[i] or 0,
                    wave_period_s=hourly.get("wave_period", [0])[i] or 0,
                    wind_wave_height_m=hourly.get("wind_wave_height", [0])[i] or 0,
                    swell_height_m=hourly.get("swell_wave_height", [0])[i] or 0,
                    swell_direction=hourly.get("swell_wave_direction", [0])[i] or 0,
                    timestamp=datetime.fromisoformat(time_str)
                ))
            
            return results
        except httpx.HTTPError as e:
            logger.error(f"OpenMeteo Marine API error: {e}")
            raise
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


_adapter_instance: Optional[OpenMeteoAdapter] = None

def get_openmeteo_adapter() -> OpenMeteoAdapter:
    """Get or create OpenMeteo adapter instance."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = OpenMeteoAdapter()
    return _adapter_instance
