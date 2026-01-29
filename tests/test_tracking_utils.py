"""
Tests for LARA utility functions.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking.utils import (
    haversine_distance,
    get_bounding_box,
    format_altitude,
    format_speed,
    format_duration,
    validate_coordinates,
    parse_state_vector,
)


class TestHaversineDistance:
    """Tests for haversine_distance function."""

    def test_same_point(self):
        """Distance between same point should be 0."""
        dist = haversine_distance(49.3508, 8.1364, 49.3508, 8.1364)
        assert dist == 0.0

    def test_known_distance(self):
        """Test with known distance."""
        # Roughly 100km from Neustadt to Frankfurt
        dist = haversine_distance(49.3508, 8.1364, 50.1109, 8.6821)
        assert 80 < dist < 120  # Allow for some margin

    def test_negative_coordinates(self):
        """Test with negative coordinates."""
        dist = haversine_distance(-33.8688, 151.2093, -37.8136, 144.9631)
        assert dist > 0  # Sydney to Melbourne


class TestBoundingBox:
    """Tests for get_bounding_box function."""

    def test_bounding_box_structure(self):
        """Bounding box should return 4 values."""
        result = get_bounding_box(49.3508, 8.1364, 50)
        assert len(result) == 4
        lat_min, lon_min, lat_max, lon_max = result
        assert lat_min < lat_max
        assert lon_min < lon_max

    def test_center_in_box(self):
        """Center point should be in bounding box."""
        lat, lon = 49.3508, 8.1364
        lat_min, lon_min, lat_max, lon_max = get_bounding_box(lat, lon, 50)
        assert lat_min < lat < lat_max
        assert lon_min < lon < lon_max

    def test_radius_zero(self):
        """Zero radius should return same point."""
        lat, lon = 49.3508, 8.1364
        lat_min, lon_min, lat_max, lon_max = get_bounding_box(lat, lon, 0)
        assert lat_min == pytest.approx(lat, rel=1e-10)
        assert lat_max == pytest.approx(lat, rel=1e-10)


class TestFormatting:
    """Tests for formatting functions."""

    def test_format_altitude(self):
        """Test altitude formatting."""
        assert "10000 m" in format_altitude(10000)
        assert "ft" in format_altitude(10000)
        assert format_altitude(None) == "N/A"

    def test_format_speed(self):
        """Test speed formatting."""
        assert "360.0 km/h" == format_speed(100, "kmh")
        assert "100.0 m/s" == format_speed(100, "ms")
        assert "knots" in format_speed(100, "knots")
        assert format_speed(None) == "N/A"

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(3665) == "1h 1m 5s"
        assert format_duration(60) == "1m"
        assert format_duration(0) == "0s"
        assert format_duration(None) == "N/A"
        assert format_duration(-1) == "N/A"


class TestValidateCoordinates:
    """Tests for coordinate validation."""

    def test_valid_coordinates(self):
        """Valid coordinates should return True."""
        assert validate_coordinates(49.3508, 8.1364) is True
        assert validate_coordinates(0, 0) is True
        assert validate_coordinates(-90, -180) is True
        assert validate_coordinates(90, 180) is True

    def test_invalid_coordinates(self):
        """Invalid coordinates should return False."""
        assert validate_coordinates(100, 0) is False
        assert validate_coordinates(0, 200) is False
        assert validate_coordinates(-100, 0) is False
        assert validate_coordinates(0, -200) is False


class TestParseStateVector:
    """Tests for parse_state_vector function."""

    def test_parse_basic_state(self):
        """Test parsing basic state vector."""
        state = [
            "abc123",  # icao24
            "DLH123 ",  # callsign
            "Germany",  # origin_country
            1234567890,  # time_position
            1234567890,  # last_contact
            8.1364,  # longitude
            49.3508,  # latitude
            10000,  # baro_altitude
            False,  # on_ground
            250,  # velocity
            90,  # true_track
            0,  # vertical_rate
            None,  # sensors
            10050,  # geo_altitude
            "1200",  # squawk
        ]

        result = parse_state_vector(state)

        assert result["icao24"] == "abc123"
        assert result["callsign"] == "DLH123"
        assert result["origin_country"] == "Germany"
        assert result["longitude"] == 8.1364
        assert result["latitude"] == 49.3508
        assert result["baro_altitude"] == 10000
        assert result["on_ground"] is False
        assert result["velocity"] == 250
        assert result["squawk"] == "1200"

    def test_parse_null_callsign(self):
        """Test parsing state with null callsign."""
        state = ["abc123", None, "Germany"] + [None] * 12
        result = parse_state_vector(state)
        assert result["callsign"] is None

    def test_parse_short_state(self):
        """Test parsing state vector without squawk."""
        state = ["abc123"] + [None] * 13
        result = parse_state_vector(state)
        assert result["squawk"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
