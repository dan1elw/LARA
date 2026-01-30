"""
Tests for configuration management.
"""

import pytest
from lara.config import Config


@pytest.fixture
def sample_config():
    """Get default configuration."""
    return str(
        {
            "location": {
                "latitude": 48.8566,
                "longitude": 2.3522,
                "name": "Paris, France",
            },
            "tracking": {
                "radius_km": 30,
                "update_interval_seconds": 10,
            },
            "database": {"path": "data/lara_flights_paris.db"},
            "api": {
                "opensky_url": "https://opensky-network.org/api/states/all",
                "timeout_seconds": 10,
                "credentials_path": "custom_credentials.json",
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        }
    )


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        """Test loading default configuration."""
        config = Config(config_path="non_existent_config.yaml")
        assert config._config["location"]["name"] == "Berlin Brandenburger Tor, Germany"
        assert config._config["tracking"]["radius_km"] == 25
        assert config._config["database"]["path"] == "data/lara_flights_berlin.db"

        config = Config(config_path=None)
        assert config._config["location"]["name"] == "Berlin Brandenburger Tor, Germany"
        assert config._config["tracking"]["radius_km"] == 25
        assert config._config["database"]["path"] == "data/lara_flights_berlin.db"

    def test_custom_config(self, tmp_path, sample_config):
        """Test loading custom configuration from YAML file."""
        custom_config_path = tmp_path / "custom_config.yaml"
        custom_config_content = sample_config
        custom_config_path.write_text(custom_config_content)
        config = Config(config_path=str(custom_config_path))
        assert config._config["location"]["name"] == "Paris, France"
        assert config._config["tracking"]["radius_km"] == 30
        assert config._config["database"]["path"] == "data/lara_flights_paris.db"

    def test_save_config(self, tmp_path, sample_config):
        """Test saving configuration to YAML file."""
        custom_config_path = tmp_path / "custom_config.yaml"
        custom_config_content = sample_config
        custom_config_path.write_text(custom_config_content)
        config = Config(config_path=str(custom_config_path))

        # Modify a value and save
        config._config["tracking"]["radius_km"] = 50
        config.save_config()

        # Reload and verify change
        reloaded_config = Config(config_path=str(custom_config_path))
        assert reloaded_config._config["tracking"]["radius_km"] == 50

    def test_malformed_config(self, tmp_path):
        """Test handling of malformed configuration file."""
        malformed_config_path = tmp_path / "malformed_config.yaml"
        malformed_config_content = """
location:
  latitude: not_a_number
  longitude: 2.3522
"""
        malformed_config_path.write_text(malformed_config_content)
        config = Config(config_path=str(malformed_config_path))
        # Should fall back to default config
        assert config._config["location"]["name"] == "Berlin Brandenburger Tor, Germany"
        assert config._config["tracking"]["radius_km"] == 25
