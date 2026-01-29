"""
Tests for improved corridor detection system.

Tests cover:
1. Linear corridor detection
2. Directional grouping
3. Line fitting algorithms
4. Quality metrics (linearity)
5. Edge cases and error handling
"""

import pytest
import sqlite3
import tempfile
import os

# Import the module to test
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.analysis.corridor_detector import (
    CorridorDetector,
    Position,
    LineSegment,
    Corridor,
)

from lara.analysis.constants import MIN_LINEARITY_SCORE, MIN_CORRIDOR_LENGTH_KM


@pytest.fixture
def linear_corridor_db():
    """
    Create a database with positions forming a clear linear corridor.

    Creates positions along a north-south corridor (heading ~0/180°)
    with multiple flights following the same path.
    """
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

    # Create 15 flights along a north-south corridor
    # Starting at 49.0°N, 8.0°E, heading north to 49.5°N
    base_lat = 49.0
    base_lon = 8.0

    for flight_num in range(15):
        cursor.execute(
            "INSERT INTO flights (icao24, callsign, origin_country) VALUES (?, ?, ?)",
            (f"abc{flight_num:03d}", f"TEST{flight_num}", "Germany"),
        )
        flight_id = cursor.lastrowid

        # Add positions along north-south path
        # Each flight has slight variation in longitude (±0.01°)
        lon_offset = (flight_num - 7) * 0.002  # Spread around corridor

        for point in range(10):
            lat = base_lat + point * 0.05  # Move north
            lon = base_lon + lon_offset
            heading = 0.0 if point < 9 else 180.0  # North (with return at end)

            cursor.execute(
                """
                INSERT INTO positions (flight_id, latitude, longitude, altitude_m, heading)
                VALUES (?, ?, ?, ?, ?)
            """,
                (flight_id, lat, lon, 10000, heading),
            )

    conn.commit()
    yield conn

    conn.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def multi_corridor_db():
    """
    Create a database with multiple distinct corridors.

    Creates:
    1. North-South corridor (heading 0°)
    2. East-West corridor (heading 90°)
    3. Northeast corridor (heading 45°)
    """
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

    corridors = [
        # (heading, lat_delta_per_step, lon_delta_per_step, num_flights)
        (0, 0.05, 0.0, 12),  # North-South
        (90, 0.0, 0.05, 8),  # East-West
        (45, 0.035, 0.035, 6),  # Northeast
    ]

    base_lat = 49.0
    base_lon = 8.0

    for corridor_heading, lat_delta, lon_delta, num_flights in corridors:
        for flight_num in range(num_flights):
            cursor.execute(
                "INSERT INTO flights (icao24, callsign, origin_country) VALUES (?, ?, ?)",
                (
                    f"corridor{int(corridor_heading)}_{flight_num}",
                    f"COR{int(corridor_heading)}",
                    "Germany",
                ),
            )
            flight_id = cursor.lastrowid

            # Add positions along corridor path
            for point in range(8):
                lat = base_lat + point * lat_delta + flight_num * 0.001
                lon = base_lon + point * lon_delta + flight_num * 0.001

                cursor.execute(
                    """
                    INSERT INTO positions (flight_id, latitude, longitude, altitude_m, heading)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (flight_id, lat, lon, 10000, corridor_heading),
                )

    conn.commit()
    yield conn

    conn.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestCorridorDetector:
    """Test suite for CorridorDetector class."""

    def test_initialization(self, linear_corridor_db):
        """Test detector initialization."""
        detector = CorridorDetector(linear_corridor_db)
        assert detector.conn is not None

    def test_load_positions(self, linear_corridor_db):
        """Test position loading from database."""
        detector = CorridorDetector(linear_corridor_db)
        positions = detector._load_positions()

        assert len(positions) > 0
        assert all(isinstance(p, Position) for p in positions)
        assert all(p.latitude is not None for p in positions)
        assert all(p.longitude is not None for p in positions)
        assert all(p.heading is not None for p in positions)

    def test_detect_single_corridor(self, linear_corridor_db):
        """Test detection of a single clear corridor."""
        detector = CorridorDetector(linear_corridor_db)
        result = detector.detect_corridors(min_flights=5)

        assert result["total_corridors"] >= 1
        assert len(result["corridors"]) >= 1

        # Check first corridor
        corridor = result["corridors"][0]
        assert corridor["unique_flights"] >= 5
        assert corridor["linearity_score"] > 0.5
        assert corridor["length_km"] > 5.0

        # Should be roughly north-south (heading ~0 or ~180)
        heading = corridor["heading"]
        assert heading < 30 or heading > 330

    def test_detect_multiple_corridors(self, multi_corridor_db):
        """Test detection of multiple distinct corridors."""
        detector = CorridorDetector(multi_corridor_db)
        result = detector.detect_corridors(min_flights=3)

        # Should detect at least 2 of the 3 corridors
        assert result["total_corridors"] >= 2

        # Check that corridors have different headings
        headings = [c["heading"] for c in result["corridors"][:3]]
        # Headings should be significantly different
        for i in range(len(headings)):
            for j in range(i + 1, len(headings)):
                diff = abs(headings[i] - headings[j])
                # Either significantly different or opposite directions
                assert diff > 20 or diff > 160

    def test_corridor_ranking(self, multi_corridor_db):
        """Test that corridors are properly ranked by traffic."""
        detector = CorridorDetector(multi_corridor_db)
        result = detector.detect_corridors(min_flights=3)

        corridors = result["corridors"]

        # Check ranking order
        for i in range(len(corridors) - 1):
            assert corridors[i]["rank"] == i + 1
            # Higher ranked should have more or equal flights
            assert corridors[i]["unique_flights"] >= corridors[i + 1]["unique_flights"]

    def test_linearity_score(self, linear_corridor_db):
        """Test linearity score calculation."""
        detector = CorridorDetector(linear_corridor_db)
        positions = detector._load_positions()

        # Group positions (should form one group)
        groups = detector._group_by_direction_and_proximity(positions, 30.0, 2.0)

        assert len(groups) > 0

        # Fit corridor to first group
        corridor = detector._fit_corridor(groups[0])

        assert corridor is not None
        # Linear corridor should have high linearity score
        assert corridor.linearity_score > 0.6

    def test_haversine_distance(self, linear_corridor_db):
        """Test Haversine distance calculation."""
        detector = CorridorDetector(linear_corridor_db)

        # Test known distance (roughly)
        # 1 degree latitude ~ 111 km
        dist = detector._haversine_distance(49.0, 8.0, 50.0, 8.0)
        assert 110 < dist < 112  # ~111 km

        # Test same point
        dist = detector._haversine_distance(49.0, 8.0, 49.0, 8.0)
        assert dist == 0.0

    def test_bearing_calculation(self, linear_corridor_db):
        """Test bearing/heading calculation."""
        detector = CorridorDetector(linear_corridor_db)

        # North: should be ~0°
        bearing = detector._calculate_bearing(49.0, 8.0, 50.0, 8.0)
        assert -5 < bearing < 5 or bearing > 355

        # East: should be ~90°
        bearing = detector._calculate_bearing(49.0, 8.0, 49.0, 9.0)
        assert 85 < bearing < 95

        # South: should be ~180°
        bearing = detector._calculate_bearing(50.0, 8.0, 49.0, 8.0)
        assert 175 < bearing < 185

        # West: should be ~270°
        bearing = detector._calculate_bearing(49.0, 9.0, 49.0, 8.0)
        assert 265 < bearing < 275

    def test_line_fitting(self, linear_corridor_db):
        """Test least squares line fitting."""
        detector = CorridorDetector(linear_corridor_db)

        # Create test points along a line
        lats = [49.0, 49.1, 49.2, 49.3, 49.4]
        lons = [8.0, 8.0, 8.0, 8.0, 8.0]

        line = detector._fit_line_least_squares(lats, lons)

        assert line is not None
        assert isinstance(line, LineSegment)

        # Line should be vertical (north-south)
        assert abs(line.start_lon - line.end_lon) < 0.001

        # Length should be ~44 km (0.4 degrees * 111 km/degree)
        assert 40 < line.length_km < 48

    def test_perpendicular_distance(self, linear_corridor_db):
        """Test perpendicular distance calculation."""
        detector = CorridorDetector(linear_corridor_db)

        # Create vertical line
        line = LineSegment(
            start_lat=49.0,
            start_lon=8.0,
            end_lat=50.0,
            end_lon=8.0,
            heading=0.0,
            length_km=111.0,
        )

        # Point on the line
        dist = detector._perpendicular_distance(49.5, 8.0, line)
        assert dist < 0.1  # Should be very close to 0

        # Point 0.1 degrees away (~ 11 km)
        dist = detector._perpendicular_distance(49.5, 8.1, line)
        assert 10 < dist < 12

    def test_directional_grouping(self, multi_corridor_db):
        """Test that positions are grouped by direction."""
        detector = CorridorDetector(multi_corridor_db)
        positions = detector._load_positions()

        groups = detector._group_by_direction_and_proximity(
            positions, 30.0, 5.0  # Wider tolerance for this test
        )

        # Should create at least 3 groups (one per corridor)
        assert len(groups) >= 3

        # Each group should have consistent headings
        for group in groups:
            headings = [p.heading for p in group if p.heading is not None]
            if len(headings) > 1:
                avg_heading = sum(headings) / len(headings)
                # All headings should be close to average
                for h in headings:
                    diff = min(abs(h - avg_heading), 360 - abs(h - avg_heading))
                    assert diff < 45  # Within 45 degrees

    def test_minimum_flights_filter(self, linear_corridor_db):
        """Test minimum flights filter."""
        detector = CorridorDetector(linear_corridor_db)

        # With high threshold, should get fewer corridors
        result_high = detector.detect_corridors(min_flights=20)
        result_low = detector.detect_corridors(min_flights=3)

        assert result_low["total_corridors"] >= result_high["total_corridors"]

    def test_quality_filters(self, linear_corridor_db):
        """Test that quality filters are applied."""
        detector = CorridorDetector(linear_corridor_db)
        result = detector.detect_corridors(min_flights=5)

        # All corridors should meet quality thresholds
        for corridor in result["corridors"]:
            assert corridor["linearity_score"] >= MIN_LINEARITY_SCORE
            assert corridor["length_km"] >= MIN_CORRIDOR_LENGTH_KM

    def test_corridor_to_dict(self, linear_corridor_db):
        """Test corridor serialization to dictionary."""
        detector = CorridorDetector(linear_corridor_db)

        corridor = Corridor(
            rank=1,
            center_lat=49.25,
            center_lon=8.0,
            heading=0.0,
            length_km=50.0,
            width_km=2.0,
            unique_flights=10,
            total_positions=100,
            avg_altitude_m=10000.0,
            linearity_score=0.9,
            start_lat=49.0,
            start_lon=8.0,
            end_lat=49.5,
            end_lon=8.0,
        )

        result = detector._corridor_to_dict(corridor)

        assert isinstance(result, dict)
        assert result["rank"] == 1
        assert result["center_lat"] == 49.25
        assert result["unique_flights"] == 10
        assert result["start_lat"] == 49.0
        assert result["end_lat"] == 49.5

    def test_empty_database(self):
        """Test behavior with empty database."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create full schema expected by CorridorDetector
        cursor.execute("""
            CREATE TABLE flights (
                id INTEGER PRIMARY KEY,
                callsign TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE positions (
                id INTEGER PRIMARY KEY,
                flight_id INTEGER,
                latitude REAL,
                longitude REAL,
                altitude_m REAL,
                heading REAL,
                FOREIGN KEY (flight_id) REFERENCES flights(id)
            )
        """)

        conn.commit()

        detector = CorridorDetector(conn)
        result = detector.detect_corridors()

        assert result["total_corridors"] == 0
        assert result["corridors"] == []

        conn.close()
        os.unlink(db_path)

    def test_insufficient_data(self, linear_corridor_db):
        """Test behavior with insufficient data."""
        detector = CorridorDetector(linear_corridor_db)

        # Request extremely high minimum flights
        result = detector.detect_corridors(min_flights=1000)

        # Should return empty or very few results
        assert result["total_corridors"] < 5


class TestDataStructures:
    """Test data structures used in corridor detection."""

    def test_position_dataclass(self):
        """Test Position dataclass."""
        pos = Position(
            latitude=49.35,
            longitude=8.14,
            altitude_m=10000.0,
            heading=45.0,
            flight_id=1,
            callsign="TEST123",
        )

        assert pos.latitude == 49.35
        assert pos.longitude == 8.14
        assert pos.altitude_m == 10000.0
        assert pos.heading == 45.0

    def test_line_segment_dataclass(self):
        """Test LineSegment dataclass."""
        line = LineSegment(
            start_lat=49.0,
            start_lon=8.0,
            end_lat=49.5,
            end_lon=8.5,
            heading=45.0,
            length_km=70.0,
        )

        # Test midpoint calculation
        mid_lat, mid_lon = line.midpoint()
        assert mid_lat == 49.25
        assert mid_lon == 8.25

    def test_corridor_dataclass(self):
        """Test Corridor dataclass."""
        corridor = Corridor(
            rank=1,
            center_lat=49.25,
            center_lon=8.25,
            heading=45.0,
            length_km=70.0,
            width_km=2.0,
            unique_flights=15,
            total_positions=150,
            avg_altitude_m=10000.0,
            linearity_score=0.85,
            start_lat=49.0,
            start_lon=8.0,
            end_lat=49.5,
            end_lon=8.5,
        )

        assert corridor.rank == 1
        assert corridor.unique_flights == 15
        assert 0 <= corridor.linearity_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
