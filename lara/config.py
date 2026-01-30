"""
LARA Configuration Management
"""

import yaml
import os
from typing import Dict, Any


class Constants():
    EARTH_RADIUS_KM = 6371      # 
    METERS_TO_FEET = 3.28084    # 
    MS_TO_KMH = 3.6             # 
    KM_PER_DEGREE_LAT = 111.32  # Approximate conversion at equator


class Settings():
    """Tracking Settings"""
    FLIGHT_SESSION_TIMEOUT_MINUTES = 30     # A flight is considered the same if it has the same ICAO24 and callsign, and was last seen within FLIGHT_SESSION_TIMEOUT_MINUTES.
    MIN_UPDATE_INTERVAL = 10                # OpenSky rate limit
    ALTITUDE_RANGES = [                     # 
        (0, 1000, "0-1000m"),
        (1000, 3000, "1000-3000m"),
        (3000, 6000, "3000-6000m"),
        (6000, 9000, "6000-9000m"),
        (9000, 12000, "9000-12000m"),
        (12000, float("inf"), "12000m+"),
    ]
    SCHEMA_VERSION = "1.0.0"                # 

    """Analysis Settings"""
    HEADING_TOLERANCE_DEG: float = 20.0     # Corridor analysis Positions within ±20° are same direction
    PROXIMITY_THRESHOLD_KM: float = 10.0    # Positions within 10km can belong to same corridor
    MIN_CORRIDOR_LENGTH_KM: float = 3.0     # Minimum corridor length (lowered to 3km)
    MIN_LINEARITY_SCORE: float = 0.3        # Minimum linearity (0-1, lowered to 0.5)
    MIN_FLIGHTS_FOR_CORRIDOR: int = 15      # Minimum unique flights to qualify as corridor
    PEAK_HOUR_THRESHOLD = 0.7               # Time analysis 70% of max hourly traffic
    DAYS_FOR_TREND_ANALYSIS = 30            # Time analysis
    MIN_PATTERN_OCCURRENCES = 5             # Pattern detection
    ROUTE_SIMILARITY_THRESHOLD = 0.8        # Pattern detection 80% similarity
    ALTITUDE_CLASSES = {                    # Altitude classifications (meters)
        "very_low": (0, 1000),
        "low": (1000, 3000),
        "medium": (3000, 6000),
        "high": (6000, 9000),
        "very_high": (9000, 12000),
        "cruise": (12000, float("inf")),
    }
    DISTANCE_CLASSES = {                    # Distance classifications (km)
        "very_close": (0, 5),
        "close": (5, 10),
        "medium": (10, 20),
        "far": (20, 30),
        "very_far": (30, float("inf")),
    }

    """Visualization Settings"""
    DEFAULT_MAP_STYLE = "CartoDB.Positron"
    DEFAULT_ZOOM = 10
    FLIGHT_PATH_WEIGHT = 2
    FLIGHT_PATH_OPACITY = 0.6
    MARKER_RADIUS = 8                       # Marker styles
    MARKER_OPACITY = 0.7
    MARKER_FILL_OPACITY = 0.5
    CORRIDOR_OPACITY = 0.3                  # Corridor visualization
    CORRIDOR_BORDER_WEIGHT = 2


class Colors():
    ALTITUDE_COLORS = {
        "very_low": "#ff3b3b",  # 0 - 1000 m
        "low": "#ff7a18",  # 1000 - 3000 m
        "medium": "#f5e663",  # 3000 - 6000 m
        "high": "#00e5a8",  # 6000 - 9000 m
        "very_high": "#00b4ff",  # 9000 - 12000 m
        "cruise": "#7c3aed",  # 12000+ m
    }
    RANKED_COLORS = [
        "#e74c3c",  # Rank 1 - Red (highest traffic)
        "#f17c15",  # Rank 2 - Orange
        "#ffd015",  # Rank 3 - Yellow
        "#2ecc71",  # Rank 4-5 - Green
        "#3498db",  # Rank 6+ - Blue
    ]
    HEATMAP_GRADIENT = {  # Neon Plasma
        0.0: "#120018",
        0.25: "#6a00ff",
        0.5: "#ff2fd2",
        0.75: "#ff9f1c",
        1.0: "#fff200",
    }
    FLIGHT_PATH_COLOR = "#3498db"


class Config:
    """Configuration manager for LARA application."""

    def __init__(self, config_path: str = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if (self.config_path is None) or (not os.path.exists(self.config_path)):
            return self._get_default_config()

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                if not self._validate_config(config):
                    return self._get_default_config()
                else:
                    return config
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            return self._get_default_config()
        
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and types."""
        # Basic validation can be extended as needed
        try:
            assert "location" in config
            assert "latitude" in config["location"]
            assert "longitude" in config["location"]
            assert isinstance(config["location"]["latitude"], (float, int))
            assert isinstance(config["location"]["longitude"], (float, int))

            assert "tracking" in config
            assert "radius_km" in config["tracking"]
            assert isinstance(config["tracking"]["radius_km"], (float, int))

            assert "database" in config
            assert "path" in config["database"]
            assert isinstance(config["database"]["path"], str)

            return True
        except Exception:
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "location": {
                "latitude": 52.516257,
                "longitude": 13.377525,
                "name": "Berlin Brandenburger Tor, Germany",
            },
            "tracking": {
                "radius_km": 25,
                "update_interval_seconds": 15,
            },
            "database": {"path": "data/lara_flights_berlin.db"},
            "api": {
                "opensky_url": "https://opensky-network.org/api/states/all",
                "timeout_seconds": 10,
                # OAuth2 credentials (new authentication method)
                "credentials_path": None,  # Path to credentials.json from OpenSky
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        }

    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    @property
    def home_latitude(self) -> float:
        """Get home latitude."""
        return self._config["location"]["latitude"]

    @property
    def home_longitude(self) -> float:
        """Get home longitude."""
        return self._config["location"]["longitude"]

    @property
    def location_name(self) -> str:
        """Get location name."""
        return self._config["location"].get("name", "Unknown Location")

    @property
    def radius_km(self) -> float:
        """Get tracking radius in kilometers."""
        return self._config["tracking"]["radius_km"]

    @property
    def update_interval(self) -> int:
        """Get update interval in seconds."""
        return self._config["tracking"]["update_interval_seconds"]

    @property
    def db_path(self) -> str:
        """Get database path."""
        return self._config["database"]["path"]

    @property
    def api_url(self) -> str:
        """Get OpenSky API URL."""
        return self._config["api"]["opensky_url"]

    @property
    def api_timeout(self) -> int:
        """Get API timeout in seconds."""
        return self._config["api"]["timeout_seconds"]

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'location.latitude')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'location.latitude')
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
