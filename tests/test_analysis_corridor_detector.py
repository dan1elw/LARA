"""
Tests for corridor detection.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.analysis.corridor_detector import CorridorDetector


@pytest.fixture
def sample_db():
    """Create sample database with test data."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY,
            icao24 TEXT,
            callsign TEXT,
            origin_country TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            heading REAL
        )
    """)

    # Insert test data - create a corridor
    for i in range(15):
        cursor.execute(
            "INSERT INTO flights (icao24, callsign, origin_country) VALUES (?, ?, ?)",
            (f"abc{i:03d}", f"TEST{i}", "Germany"),
        )
        flight_id = cursor.lastrowid

        # Add positions near same location (corridor)
        for j in range(5):
            cursor.execute(
                """
                INSERT INTO positions (flight_id, latitude, longitude, altitude_m, heading)
                VALUES (?, ?, ?, ?, ?)
            """,
                (flight_id, 49.35 + i * 0.001, 8.14 + i * 0.001, 10000, 90),
            )

    conn.commit()

    yield conn

    conn.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestCorridorDetector:
    """Tests for CorridorDetector class."""

    def test_init(self, sample_db):
        """Test corridor detector initialization."""
        detector = CorridorDetector(sample_db)
        assert detector.conn is not None

    def test_detect_corridors(self, sample_db):
        """Test corridor detection."""
        detector = CorridorDetector(sample_db)
        result = detector.detect_corridors(grid_size_km=5.0, min_flights=5)

        assert "total_corridors" in result
        assert "corridors" in result
        assert result["grid_size_km"] == 5.0

    def test_grid_cell_calculation(self, sample_db):
        """Test grid cell calculation."""
        detector = CorridorDetector(sample_db)

        lat, lon = detector._get_grid_cell(49.3508, 8.1364, 5.0)

        # Should round to grid
        assert isinstance(lat, float)
        assert isinstance(lon, float)

    def test_circular_mean(self, sample_db):
        """Test circular mean for headings."""
        detector = CorridorDetector(sample_db)

        # Test simple case
        mean = detector._circular_mean([0, 90, 180, 270])
        assert mean is not None

        # Test edge case (wrapping around 360)
        mean = detector._circular_mean([350, 10])
        assert 0 <= mean <= 360

    def test_min_flights_filter(self, sample_db):
        """Test minimum flights filter."""
        detector = CorridorDetector(sample_db)

        # High threshold should return fewer corridors
        result_high = detector.detect_corridors(grid_size_km=5.0, min_flights=20)
        result_low = detector.detect_corridors(grid_size_km=5.0, min_flights=1)

        assert result_high["total_corridors"] <= result_low["total_corridors"]
