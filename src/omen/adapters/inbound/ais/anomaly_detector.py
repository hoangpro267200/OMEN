"""
AIS anomaly detection.

Detects port congestion, chokepoint delays, and route deviations
using historical baselines and statistical methods.
"""

from datetime import datetime, timezone
from typing import Literal

from .schemas import PortStatus, ChokePointStatus, VesselMovement
from .config import AISConfig, PORT_METADATA, CHOKEPOINT_METADATA


class AnomalyDetector:
    """
    Detects anomalies in AIS data.

    Uses historical baselines and configurable thresholds to identify:
    - Port congestion (vessels waiting above normal)
    - Chokepoint delays (transit time above normal)
    - Route deviations (vessels off expected route)
    """

    def __init__(self, config: AISConfig | None = None):
        self.config = config or AISConfig()

    def detect_port_congestion(self, port_status: PortStatus) -> PortStatus:
        """
        Detect congestion anomaly for a port.

        Updates port_status with:
        - congestion_ratio
        - wait_time_ratio
        - anomaly_detected
        - anomaly_severity
        """
        # Calculate ratios
        port_status.congestion_ratio = port_status.calculate_congestion_ratio()
        port_status.wait_time_ratio = port_status.calculate_wait_time_ratio()

        # Detect anomaly using configurable threshold
        threshold = self.config.congestion_threshold_multiplier
        wait_threshold = self.config.wait_time_threshold_multiplier

        # Anomaly if either metric exceeds threshold
        congestion_anomaly = port_status.congestion_ratio >= threshold
        wait_anomaly = port_status.wait_time_ratio >= wait_threshold

        port_status.anomaly_detected = congestion_anomaly or wait_anomaly

        # Calculate severity
        if port_status.anomaly_detected:
            port_status.anomaly_severity = self._calculate_severity(
                max(port_status.congestion_ratio, port_status.wait_time_ratio)
            )
        else:
            port_status.anomaly_severity = "none"

        return port_status

    def detect_chokepoint_delay(self, chokepoint: ChokePointStatus) -> ChokePointStatus:
        """
        Detect delay anomaly for a chokepoint.

        Updates chokepoint with:
        - delay_ratio
        - delays_detected
        - blockage_detected
        - queue_severity
        """
        # Calculate delay ratio
        chokepoint.delay_ratio = chokepoint.calculate_delay_ratio()

        # Detect delays (1.5x normal transit time)
        delay_threshold = 1.5
        chokepoint.delays_detected = chokepoint.delay_ratio >= delay_threshold

        # Detect potential blockage (3x normal + high queue)
        blockage_threshold = 3.0
        high_queue = chokepoint.vessels_waiting > 50
        chokepoint.blockage_detected = chokepoint.delay_ratio >= blockage_threshold and high_queue

        # Calculate queue severity
        if chokepoint.blockage_detected:
            chokepoint.queue_severity = "critical"
        elif chokepoint.delays_detected:
            chokepoint.queue_severity = self._calculate_severity(chokepoint.delay_ratio)
        else:
            chokepoint.queue_severity = "none"

        return chokepoint

    def detect_route_deviation(self, movement: VesselMovement) -> VesselMovement:
        """
        Detect if vessel has deviated from expected route.

        Updates movement with:
        - deviation_km
        - deviation_detected
        - deviation_type
        """
        if not movement.expected_route:
            return movement

        # Calculate distance from nearest point on expected route
        min_distance = float("inf")
        for waypoint in movement.expected_route:
            dist = self._haversine_distance(
                movement.current_lat,
                movement.current_lon,
                waypoint[0],
                waypoint[1],
            )
            min_distance = min(min_distance, dist)

        movement.deviation_km = min_distance

        # Detect deviation using threshold
        threshold = self.config.route_deviation_threshold_km
        movement.deviation_detected = movement.deviation_km > threshold

        # Classify deviation type
        if movement.deviation_km > 500:
            movement.deviation_type = "reroute"
        elif movement.deviation_km > threshold:
            movement.deviation_type = "minor"
        else:
            movement.deviation_type = "none"

        return movement

    def _calculate_severity(
        self, ratio: float
    ) -> Literal["none", "low", "medium", "high", "critical"]:
        """
        Calculate anomaly severity based on ratio.

        - none: ratio < 1.5
        - low: 1.5 <= ratio < 2.0
        - medium: 2.0 <= ratio < 2.5
        - high: 2.5 <= ratio < 3.0
        - critical: ratio >= 3.0
        """
        if ratio < 1.5:
            return "none"
        elif ratio < 2.0:
            return "low"
        elif ratio < 2.5:
            return "medium"
        elif ratio < 3.0:
            return "high"
        else:
            return "critical"

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns distance in kilometers.
        """
        import math

        R = 6371.0  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


class MockAnomalyDetector(AnomalyDetector):
    """
    Mock anomaly detector for testing and demo purposes.

    Generates realistic anomalies based on configuration.
    """

    def __init__(
        self,
        config: AISConfig | None = None,
        congestion_ports: list[str] | None = None,
        delayed_chokepoints: list[str] | None = None,
    ):
        super().__init__(config)
        self.congestion_ports = congestion_ports or []
        self.delayed_chokepoints = delayed_chokepoints or []

    def detect_port_congestion(self, port_status: PortStatus) -> PortStatus:
        """Mock congestion detection with configurable anomalies."""
        # First run normal detection
        port_status = super().detect_port_congestion(port_status)

        # Override for mock scenarios
        if port_status.port_code in self.congestion_ports:
            port_status.anomaly_detected = True
            port_status.anomaly_severity = "high"

        return port_status

    def detect_chokepoint_delay(self, chokepoint: ChokePointStatus) -> ChokePointStatus:
        """Mock delay detection with configurable anomalies."""
        # First run normal detection
        chokepoint = super().detect_chokepoint_delay(chokepoint)

        # Override for mock scenarios
        if chokepoint.name in self.delayed_chokepoints:
            chokepoint.delays_detected = True
            chokepoint.queue_severity = "high"

        return chokepoint
