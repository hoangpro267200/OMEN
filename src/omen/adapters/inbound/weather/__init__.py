"""Weather data adapters."""
from .openmeteo_adapter import OpenMeteoAdapter, get_openmeteo_adapter, WeatherData, MarineWeather

__all__ = ["OpenMeteoAdapter", "get_openmeteo_adapter", "WeatherData", "MarineWeather"]
