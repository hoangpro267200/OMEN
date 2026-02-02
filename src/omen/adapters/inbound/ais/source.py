"""
AIS Signal Source.

Implements SignalSource interface for AIS data.
"""

import logging
from typing import Iterator, AsyncIterator

from omen.application.ports.signal_source import SignalSource
from omen.domain.models.raw_signal import RawSignalEvent
from .client import AISClient, create_ais_client, MockAISClient
from .mapper import AISMapper
from .anomaly_detector import AnomalyDetector
from .config import AISConfig

logger = logging.getLogger(__name__)


class AISSignalSource(SignalSource):
    """
    AIS data source for OMEN.

    Fetches port congestion and chokepoint status, detects anomalies,
    and converts to RawSignalEvent for pipeline processing.
    """

    def __init__(
        self,
        client: AISClient | None = None,
        mapper: AISMapper | None = None,
        anomaly_detector: AnomalyDetector | None = None,
        config: AISConfig | None = None,
    ):
        self._config = config or AISConfig()
        self._client = client or create_ais_client(self._config)
        self._mapper = mapper or AISMapper(self._config)
        self._anomaly_detector = anomaly_detector or AnomalyDetector(self._config)

    @property
    def source_name(self) -> str:
        return "ais"

    def fetch_events(self, limit: int = 100) -> Iterator[RawSignalEvent]:
        """
        Fetch AIS events (port congestion, chokepoint delays).

        Flow:
        1. Query port status for monitored ports
        2. Query chokepoint status
        3. Run anomaly detection
        4. Map anomalies to RawSignalEvent
        """
        events: list[RawSignalEvent] = []

        # 1. Check port congestion
        logger.info(f"Checking {len(self._config.monitored_ports)} ports for congestion")
        for port_code in self._config.monitored_ports:
            try:
                port_status = self._client.get_port_status(port_code)

                # Anomaly detection
                port_status = self._anomaly_detector.detect_port_congestion(port_status)

                # Map to event
                event = self._mapper.map_port_congestion(port_status)
                if event:
                    logger.info(
                        f"Port congestion detected: {port_code} "
                        f"({port_status.vessels_waiting} vessels, "
                        f"{port_status.congestion_ratio:.1f}x normal)"
                    )
                    events.append(event)

            except Exception as e:
                logger.error(f"Failed to fetch port {port_code}: {e}")
                continue

        # 2. Check chokepoints
        logger.info(f"Checking {len(self._config.monitored_chokepoints)} chokepoints for delays")
        for chokepoint_name in self._config.monitored_chokepoints:
            try:
                chokepoint_status = self._client.get_chokepoint_status(chokepoint_name)

                # Anomaly detection
                chokepoint_status = self._anomaly_detector.detect_chokepoint_delay(
                    chokepoint_status
                )

                # Map to event
                event = self._mapper.map_chokepoint_delay(chokepoint_status)
                if event:
                    logger.info(
                        f"Chokepoint delay detected: {chokepoint_name} "
                        f"({chokepoint_status.vessels_waiting} vessels waiting, "
                        f"{chokepoint_status.delay_ratio:.1f}x normal transit)"
                    )
                    events.append(event)

            except Exception as e:
                logger.error(f"Failed to fetch chokepoint {chokepoint_name}: {e}")
                continue

        logger.info(f"AIS source found {len(events)} anomaly events")

        # Return up to limit
        for event in events[:limit]:
            yield event

    async def fetch_events_async(self, limit: int = 100) -> AsyncIterator[RawSignalEvent]:
        """
        Async version of fetch_events.

        For now, wraps sync method. Can be optimized with async client later.
        """
        for event in self.fetch_events(limit):
            yield event

    def fetch_by_id(self, market_id: str) -> RawSignalEvent | None:
        """
        Fetch specific port/chokepoint status by market_id.

        market_id formats:
        - Port: "SGSIN", "CNSHA", etc. (UN/LOCODE)
        - Chokepoint: "chokepoint-suez_canal", "chokepoint-panama_canal", etc.
        """
        try:
            if market_id.startswith("chokepoint-"):
                # Extract chokepoint name
                chokepoint_key = market_id.replace("chokepoint-", "")
                chokepoint_name = chokepoint_key.replace("_", " ").title()

                chokepoint_status = self._client.get_chokepoint_status(chokepoint_name)
                chokepoint_status = self._anomaly_detector.detect_chokepoint_delay(
                    chokepoint_status
                )
                return self._mapper.map_chokepoint_delay(chokepoint_status)
            else:
                # Assume it's a port code
                port_status = self._client.get_port_status(market_id)
                port_status = self._anomaly_detector.detect_port_congestion(port_status)
                return self._mapper.map_port_congestion(port_status)

        except Exception as e:
            logger.error(f"Failed to fetch by ID {market_id}: {e}")
            return None


class MockAISSignalSource(AISSignalSource):
    """
    Mock AIS source for testing with configurable scenarios.
    """

    def __init__(
        self,
        scenario: str = "normal",
        config: AISConfig | None = None,
    ):
        """
        Initialize mock source.

        Args:
            scenario: Simulation scenario
                - "normal": Normal operations (few/no anomalies)
                - "congestion": Port congestion at major ports
                - "suez_delay": Suez Canal delays
                - "multi_crisis": Multiple simultaneous issues
            config: Optional config override
        """
        config = config or AISConfig()
        client = MockAISClient(config, scenario=scenario)
        super().__init__(client=client, config=config)
        self._scenario = scenario

    @property
    def scenario(self) -> str:
        return self._scenario


def create_ais_source(
    config: AISConfig | None = None,
    scenario: str | None = None,
) -> AISSignalSource:
    """
    Factory function to create AIS signal source.

    Args:
        config: AIS configuration
        scenario: If provided, creates mock source with scenario

    Returns:
        AISSignalSource instance
    """
    config = config or AISConfig()

    if scenario or config.provider == "mock":
        return MockAISSignalSource(
            scenario=scenario or "normal",
            config=config,
        )

    return AISSignalSource(config=config)
