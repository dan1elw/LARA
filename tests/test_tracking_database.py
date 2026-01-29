"""
Tests for LARA database operations.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking.database import FlightDatabase


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize database
    db = FlightDatabase(path)

    yield db

    # Cleanup
    try:
        os.unlink(path)
    except Exception:
        pass


class TestFlightDatabase:
    """Tests for FlightDatabase class."""

    def test_init_database(self, temp_db):
        """Test database initialization."""
        # Database should be created and initialized
        assert os.path.exists(temp_db.db_path)

    def test_create_flight(self, temp_db):
        """Test creating a flight record."""
        timestamp = datetime.now().isoformat()

        flight_id = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        assert flight_id > 0

    def test_same_flight_reuse(self, temp_db):
        """Test that same flight reuses ID."""
        timestamp = datetime.now().isoformat()

        flight_id1 = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        flight_id2 = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        assert flight_id1 == flight_id2

    def test_add_position(self, temp_db):
        """Test adding position update."""
        timestamp = datetime.now().isoformat()

        flight_id = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        state_data = {
            "latitude": 49.3508,
            "longitude": 8.1364,
            "baro_altitude": 10000,
            "geo_altitude": 10050,
            "velocity": 250,
            "true_track": 90,
            "vertical_rate": 0,
            "on_ground": False,
            "squawk": "1200",
        }

        temp_db.add_position(flight_id, state_data, 5.0, timestamp)

        # Verify position was added
        positions = temp_db.get_positions_for_flight(flight_id)
        assert len(positions) == 1
        assert positions[0]["latitude"] == 49.3508

    def test_get_statistics(self, temp_db):
        """Test getting statistics."""
        stats = temp_db.get_statistics()

        assert "total_flights" in stats
        assert "unique_aircraft" in stats
        assert "total_positions" in stats
        assert stats["total_flights"] == 0  # Empty database

    def test_get_flight_by_id(self, temp_db):
        """Test retrieving flight by ID."""
        timestamp = datetime.now().isoformat()

        flight_id = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        flight = temp_db.get_flight_by_id(flight_id)

        assert flight is not None
        assert flight["icao24"] == "abc123"
        assert flight["callsign"] == "DLH123"

    def test_get_nonexistent_flight(self, temp_db):
        """Test retrieving nonexistent flight."""
        flight = temp_db.get_flight_by_id(99999)
        assert flight is None

    def test_update_daily_stats(self, temp_db):
        """Test updating daily statistics."""
        # Create some test data
        timestamp = datetime.now().isoformat()
        flight_id = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        state_data = {
            "latitude": 49.3508,
            "longitude": 8.1364,
            "baro_altitude": 10000,
            "velocity": 250,
        }

        temp_db.add_position(flight_id, state_data, 5.0, timestamp)

        # Update daily stats
        date = datetime.now().date().isoformat()
        temp_db.update_daily_stats(date)

        # Verify stats were created
        stats = temp_db.get_statistics()
        assert stats["total_flights"] > 0


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_complete_flight_lifecycle(self, temp_db):
        """Test complete lifecycle of flight tracking."""
        timestamp = datetime.now().isoformat()

        # Create flight
        flight_id = temp_db.get_or_create_flight(
            "abc123", "DLH123", "Germany", timestamp
        )

        # Add multiple positions
        for i in range(5):
            state_data = {
                "latitude": 49.3508 + i * 0.01,
                "longitude": 8.1364 + i * 0.01,
                "baro_altitude": 10000 + i * 100,
                "velocity": 250 + i * 5,
                "true_track": 90,
                "on_ground": False,
            }
            temp_db.add_position(flight_id, state_data, 5.0 + i, timestamp)

        # Verify positions
        positions = temp_db.get_positions_for_flight(flight_id)
        assert len(positions) == 5

        # Verify flight stats updated
        flight = temp_db.get_flight_by_id(flight_id)
        assert flight["position_count"] == 5
        assert flight["min_distance_km"] == 5.0
        assert flight["max_altitude_m"] == 10400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
