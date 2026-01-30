"""
LARA Configuration Management
"""

import yaml
import os
from typing import Dict, Any


class Config:
    """Configuration manager for LARA application."""

    def __init__(self, config_path: str = "lara/config.yaml"):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            return self._get_default_config()

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                return config if config else self._get_default_config()
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            return self._get_default_config()

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
