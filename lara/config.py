"""
LARA Configuration Management

This module provides configuration management for the LARA flight tracking system.
It includes physical constants, analysis settings, visualization options, and
runtime configuration loaded from YAML files.
"""

import os
from typing import Any, Dict, Optional

import yaml

# =============================================================================
# Physical Constants
# =============================================================================


class Constants:
    """Physical constants representing real-world measurements."""

    EARTH_RADIUS_KM: float = 6371.0  # Earth's radius for distance calculations
    METERS_TO_FEET: float = 3.28084  # Altitude conversion factor
    MS_TO_KMH: float = 3.6  # Velocity conversion: m/s to km/h
    KM_PER_DEGREE_LAT: float = 111.32  # Distance per degree latitude at equator


# =============================================================================
# Analysis & Tracking Settings
# =============================================================================


class Settings:
    """Configurable settings for flight tracking and analysis algorithms."""

    # --- Flight Tracking ---
    FLIGHT_SESSION_TIMEOUT_MINUTES: int = 30  # Max gap to consider same flight
    MIN_UPDATE_INTERVAL: int = 10  # Minimum seconds between API requests

    # Altitude range definitions for classification (meters)
    ALTITUDE_RANGES = [
        (0, 1000, "0-1000m"),
        (1000, 3000, "1000-3000m"),
        (3000, 6000, "3000-6000m"),
        (6000, 9000, "6000-9000m"),
        (9000, 12000, "9000-12000m"),
        (12000, float("inf"), "12000m+"),
    ]

    # --- Corridor Detection ---
    HEADING_TOLERANCE_DEG: float = 20.0  # Angular tolerance for same direction (±deg)
    PROXIMITY_THRESHOLD_KM: float = 10.0  # Max distance to group positions (km)
    MIN_CORRIDOR_LENGTH_KM: float = 3.0  # Minimum corridor length to detect (km)
    MIN_LINEARITY_SCORE: float = 0.3  # Minimum quality score (0-1, higher=straighter)
    MIN_FLIGHTS_FOR_CORRIDOR: int = 60  # Minimum flights to qualify as corridor

    # --- Temporal Analysis ---
    PEAK_HOUR_THRESHOLD: float = 0.7  # Traffic threshold for peak hours (0-1)
    DAYS_FOR_TREND_ANALYSIS: int = 30  # Historical days to analyze for trends

    # --- Pattern Detection ---
    MIN_PATTERN_OCCURRENCES: int = 5  # Minimum repetitions to identify pattern
    ROUTE_SIMILARITY_THRESHOLD: float = 0.8  # Route similarity threshold (0-1)

    # Altitude classification boundaries (meters)
    ALTITUDE_CLASSES: Dict[str, tuple[float, float]] = {
        "very_low": (0, 1000),
        "low": (1000, 3000),
        "medium": (3000, 6000),
        "high": (6000, 9000),
        "very_high": (9000, 12000),
        "cruise": (12000, float("inf")),
    }

    # Distance classification boundaries (kilometers)
    DISTANCE_CLASSES: Dict[str, tuple[float, float]] = {
        "very_close": (0, 5),
        "close": (5, 10),
        "medium": (10, 20),
        "far": (20, 30),
        "very_far": (30, float("inf")),
    }

    # --- Visualization ---
    DEFAULT_MAP_STYLE: str = "CartoDB.Positron"  # Base map tile style
    DEFAULT_ZOOM: int = 10  # Initial map zoom level
    FLIGHT_PATH_WEIGHT: int = 2  # Flight path line thickness
    FLIGHT_PATH_OPACITY: float = 0.6  # Flight path transparency (0-1)
    MARKER_RADIUS: int = 8  # Position marker size (pixels)
    MARKER_OPACITY: float = 0.7  # Marker border transparency (0-1)
    MARKER_FILL_OPACITY: float = 0.5  # Marker fill transparency (0-1)
    CORRIDOR_OPACITY: float = 0.3  # Corridor overlay transparency (0-1)
    CORRIDOR_BORDER_WEIGHT: int = 2  # Corridor border line thickness


# =============================================================================
# Color Schemes
# =============================================================================


class Colors:
    """Color definitions for visualizations."""

    # Altitude-based color coding (hex colors)
    ALTITUDE_COLORS: Dict[str, str] = {
        "very_low": "#ff3b3b",  # Red: 0-1000m
        "low": "#ff7a18",  # Orange: 1000-3000m
        "medium": "#f5e663",  # Yellow: 3000-6000m
        "high": "#00e5a8",  # Green: 6000-9000m
        "very_high": "#00b4ff",  # Blue: 9000-12000m
        "cruise": "#7c3aed",  # Purple: 12000m+
    }

    # Traffic rank colors (most to least traffic)
    RANKED_COLORS = [
        "#e74c3c",  # Rank 1: Red (highest traffic)
        "#f17c15",  # Rank 2: Orange
        "#ffd015",  # Rank 3: Yellow
        "#2ecc71",  # Rank 4-5: Green
        "#3498db",  # Rank 6+: Blue
    ]

    # Heatmap gradient stops (neon plasma theme)
    HEATMAP_GRADIENT: Dict[float, str] = {
        0.0: "#120018",  # Dark purple
        0.25: "#6a00ff",  # Purple
        0.5: "#ff2fd2",  # Magenta
        0.75: "#ff9f1c",  # Orange
        1.0: "#fff200",  # Yellow
    }

    FLIGHT_PATH_COLOR: str = "#3498db"  # Default flight path color (blue)


# =============================================================================
# Runtime Configuration
# =============================================================================


class Config:
    """
    Runtime configuration manager for LARA.

    Loads settings from YAML files or uses sensible defaults.
    Provides property-based access to common settings.

    Example:
        >>> config = Config('config.yaml')
        >>> print(f"Tracking {config.location_name}")
        >>> print(f"Home: {config.home_latitude}°N, {config.home_longitude}°E")
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file. If None or missing,
                        uses default configuration.
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file or return defaults.

        Returns:
            Configuration dictionary
        """
        if self.config_path is None or not os.path.exists(self.config_path):
            return self._get_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if self._validate_config(config):
                    return config
                else:
                    print("Warning: Invalid config structure, using defaults")
                    return self._get_default_config()
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            return self._get_default_config()

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and required fields.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Required: location section
            assert "location" in config
            assert "latitude" in config["location"]
            assert "longitude" in config["location"]
            assert isinstance(config["location"]["latitude"], (float, int))
            assert isinstance(config["location"]["longitude"], (float, int))
            assert -90 <= config["location"]["latitude"] <= 90
            assert -180 <= config["location"]["longitude"] <= 180

            # Required: tracking section
            assert "tracking" in config
            assert "radius_km" in config["tracking"]
            assert isinstance(config["tracking"]["radius_km"], (float, int))
            assert config["tracking"]["radius_km"] > 0

            # Required: database section
            assert "database" in config
            assert "path" in config["database"]
            assert isinstance(config["database"]["path"], str)

            return True
        except (AssertionError, KeyError, TypeError):
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.

        Returns:
            Default configuration dictionary
        """
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
                "credentials_path": None,  # Path to OAuth2 credentials.json
            },
        }

    def save_config(self) -> None:
        """
        Save current configuration to YAML file.

        Raises:
            ValueError: If config_path is not set
        """
        if self.config_path is None:
            raise ValueError("Cannot save config: no config_path specified")

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")
            raise

    # --- Property Accessors ---

    @property
    def home_latitude(self) -> float:
        """Get home location latitude in degrees."""
        return float(self._config["location"]["latitude"])

    @property
    def home_longitude(self) -> float:
        """Get home location longitude in degrees."""
        return float(self._config["location"]["longitude"])

    @property
    def location_name(self) -> str:
        """Get descriptive location name."""
        return self._config["location"].get("name", "Unknown Location")

    @property
    def radius_km(self) -> float:
        """Get tracking radius in kilometers."""
        return float(self._config["tracking"]["radius_km"])

    @property
    def update_interval(self) -> int:
        """Get API update interval in seconds."""
        return int(self._config["tracking"]["update_interval_seconds"])

    @property
    def db_path(self) -> str:
        """Get database file path."""
        return self._config["database"]["path"]

    # --- Generic Accessors ---

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'location.latitude')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('tracking.radius_km', 25)
            50
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

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation.

        Args:
            key: Dot-separated key path (e.g., 'location.latitude')
            value: Value to set

        Example:
            >>> config.set('tracking.radius_km', 50)
        """
        keys = key.split(".")
        config = self._config

        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set final value
        config[keys[-1]] = value
