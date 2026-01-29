"""
Tests for LARA Flight Reader.

This test suite covers:
- FlightReader initialization and database connection
- Overview statistics queries
- Recent flights retrieval with time filtering
- Top airlines and country analysis
- Temporal distribution (hourly, daily)
- Altitude distribution analysis
- Closest flights queries
- Flight search by callsign
- Flight route retrieval
- Error handling and edge cases
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking.reader import FlightReader

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_db() -> str:
    """Create an empty database with schema but no data."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao24 TEXT NOT NULL,
            callsign TEXT,
            origin_country TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            min_distance_km REAL,
            max_altitude_m REAL,
            min_altitude_m REAL,
            position_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            velocity_ms REAL,
            heading REAL,
            distance_from_home_km REAL,
            on_ground BOOLEAN
        )
    """)

    cursor.execute("""
        CREATE TABLE daily_stats (
            date DATE PRIMARY KEY,
            total_flights INTEGER,
            total_positions INTEGER,
            avg_altitude_m REAL,
            min_distance_km REAL
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def populated_db() -> str:
    """Create a database with sample flight data."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            icao24 TEXT NOT NULL,
            callsign TEXT,
            origin_country TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            min_distance_km REAL,
            max_altitude_m REAL,
            min_altitude_m REAL,
            position_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            velocity_ms REAL,
            heading REAL,
            distance_from_home_km REAL,
            on_ground BOOLEAN
        )
    """)

    cursor.execute("""
        CREATE TABLE daily_stats (
            date DATE PRIMARY KEY,
            total_flights INTEGER,
            total_positions INTEGER,
            avg_altitude_m REAL,
            min_distance_km REAL
        )
    """)

    # Insert sample flights
    base_time = datetime.now()

    # Recent flights (last 24 hours)
    for i in range(10):
        timestamp = (base_time - timedelta(hours=i)).isoformat()
        cursor.execute(
            """
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen, 
             min_distance_km, max_altitude_m, min_altitude_m, position_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f"abc{i:03d}",
                f"DLH{i:03d}",
                "Germany" if i % 2 == 0 else "France",
                timestamp,
                timestamp,
                5.0 + i,
                10000 + i * 100,
                9500 + i * 100,
                5,
            ),
        )

        flight_id = cursor.lastrowid

        # Add positions for each flight
        for j in range(5):
            pos_time = (base_time - timedelta(hours=i, minutes=j * 5)).isoformat()
            cursor.execute(
                """
                INSERT INTO positions 
                (flight_id, timestamp, latitude, longitude, altitude_m, 
                 velocity_ms, heading, distance_from_home_km, on_ground)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    flight_id,
                    pos_time,
                    49.35 + i * 0.01,
                    8.14 + i * 0.01,
                    10000 + j * 100,
                    250.0,
                    90.0,
                    5.0 + i + j * 0.5,
                    False,
                ),
            )

    # Older flights (beyond 24 hours)
    for i in range(5):
        timestamp = (base_time - timedelta(days=2 + i)).isoformat()
        cursor.execute(
            """
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen,
             min_distance_km, max_altitude_m, min_altitude_m, position_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f"xyz{i:03d}",
                f"AFR{i:03d}",
                "France",
                timestamp,
                timestamp,
                10.0 + i,
                11000,
                10500,
                3,
            ),
        )

        flight_id = cursor.lastrowid

        # Add positions
        for j in range(3):
            pos_time = (base_time - timedelta(days=2 + i, minutes=j * 5)).isoformat()
            cursor.execute(
                """
                INSERT INTO positions
                (flight_id, timestamp, latitude, longitude, altitude_m,
                 velocity_ms, heading, distance_from_home_km, on_ground)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    flight_id,
                    pos_time,
                    49.40 + i * 0.01,
                    8.20 + i * 0.01,
                    11000,
                    240.0,
                    85.0,
                    10.0 + i,
                    False,
                ),
            )

    # Add daily stats
    for i in range(7):
        date = (base_time - timedelta(days=i)).date().isoformat()
        cursor.execute(
            """
            INSERT INTO daily_stats (date, total_flights, total_positions, avg_altitude_m, min_distance_km)
            VALUES (?, ?, ?, ?, ?)
        """,
            (date, 10 - i, 50 - i * 5, 10000.0, 5.0 + i),
        )

    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def reader_with_data(populated_db: str) -> FlightReader:
    """Create FlightReader instance with populated database."""
    reader = FlightReader(populated_db)
    yield reader
    reader.close()


# ============================================================================
# Initialization Tests
# ============================================================================


class TestFlightReaderInitialization:
    """Tests for FlightReader initialization and connection."""

    def test_init_with_valid_database(self, populated_db: str):
        """Test initialization with valid database."""
        reader = FlightReader(populated_db)

        assert reader.db_path == populated_db
        assert reader.conn is not None
        assert reader.conn.row_factory == sqlite3.Row

        reader.close()

    def test_init_with_nonexistent_database(self):
        """Test initialization with nonexistent database fails gracefully."""
        with pytest.raises(sqlite3.OperationalError):
            _ = FlightReader("/nonexistent/database.db")

    def test_close_connection(self, populated_db: str):
        """Test closing database connection."""
        reader = FlightReader(populated_db)
        assert reader.conn is not None

        reader.close()

        # Connection should be closed, further queries should fail
        with pytest.raises(sqlite3.ProgrammingError):
            reader.conn.execute("SELECT 1")

    def test_close_already_closed(self, populated_db: str):
        """Test that closing already closed connection doesn't raise error."""
        reader = FlightReader(populated_db)
        reader.close()
        reader.close()  # Should not raise


# ============================================================================
# Overview Statistics Tests
# ============================================================================


class TestGetOverview:
    """Tests for get_overview method."""

    def test_overview_with_empty_database(self, empty_db: str):
        """Test overview with empty database returns zeros."""
        reader = FlightReader(empty_db)

        overview = reader.get_overview()

        assert overview["total_flights"] == 0
        assert overview["unique_aircraft"] == 0
        assert overview["total_positions"] == 0
        assert overview["avg_altitude_m"] == 0
        assert overview["closest_approach_km"] is None
        assert overview["first_observation"] is None
        assert overview["last_observation"] is None

        reader.close()

    def test_overview_with_populated_database(self, reader_with_data: FlightReader):
        """Test overview with populated database."""
        overview = reader_with_data.get_overview()

        # Should have 15 total flights (10 recent + 5 older)
        assert overview["total_flights"] == 15

        # Should have 15 unique aircraft
        assert overview["unique_aircraft"] == 15

        # Should have positions (10*5 + 5*3 = 65)
        assert overview["total_positions"] == 65

        # Average altitude should be reasonable
        assert 9000 < overview["avg_altitude_m"] < 12000

        # Closest approach should be minimum distance
        assert overview["closest_approach_km"] is not None
        assert overview["closest_approach_km"] >= 5.0

        # Timestamps should exist
        assert overview["first_observation"] is not None
        assert overview["last_observation"] is not None

    def test_overview_structure(self, reader_with_data: FlightReader):
        """Test that overview returns all expected keys."""
        overview = reader_with_data.get_overview()

        expected_keys = {
            "total_flights",
            "unique_aircraft",
            "total_positions",
            "avg_altitude_m",
            "closest_approach_km",
            "first_observation",
            "last_observation",
        }

        assert set(overview.keys()) == expected_keys


# ============================================================================
# Recent Flights Tests
# ============================================================================


class TestGetRecentFlights:
    """Tests for get_recent_flights method."""

    def test_recent_flights_default_24_hours(self, reader_with_data: FlightReader):
        """Test getting recent flights with default 24 hour window."""
        flights = reader_with_data.get_recent_flights()

        # Should return 10 flights from last 24 hours
        assert len(flights) == 10

        # All flights should be recent
        cutoff = datetime.now() - timedelta(hours=24)
        for flight in flights:
            flight_time = datetime.fromisoformat(flight["first_seen"])
            assert flight_time >= cutoff

    def test_recent_flights_custom_hours(self, reader_with_data: FlightReader):
        """Test getting recent flights with custom time window."""
        # Get flights from last 2 hours (should be fewer)
        flights = reader_with_data.get_recent_flights(hours=2)

        assert len(flights) <= 10

        # Verify time window
        cutoff = datetime.now() - timedelta(hours=2)
        for flight in flights:
            flight_time = datetime.fromisoformat(flight["first_seen"])
            assert flight_time >= cutoff

    def test_recent_flights_with_limit(self, reader_with_data: FlightReader):
        """Test limiting number of returned flights."""
        flights = reader_with_data.get_recent_flights(hours=24, limit=5)

        assert len(flights) <= 5

    def test_recent_flights_sorted_by_time(self, reader_with_data: FlightReader):
        """Test that flights are sorted by first_seen descending."""
        flights = reader_with_data.get_recent_flights()

        if len(flights) > 1:
            for i in range(len(flights) - 1):
                time1 = datetime.fromisoformat(flights[i]["first_seen"])
                time2 = datetime.fromisoformat(flights[i + 1]["first_seen"])
                assert time1 >= time2

    def test_recent_flights_includes_duration(self, reader_with_data: FlightReader):
        """Test that duration is calculated correctly."""
        flights = reader_with_data.get_recent_flights()

        for flight in flights:
            assert "duration_minutes" in flight
            # Duration should be calculated from first_seen to last_seen
            if flight["first_seen"] and flight["last_seen"]:
                first = datetime.fromisoformat(flight["first_seen"])
                last = datetime.fromisoformat(flight["last_seen"])
                expected_duration = int((last - first).total_seconds() / 60)
                assert flight["duration_minutes"] == expected_duration

    def test_recent_flights_empty_result(self, empty_db: str):
        """Test recent flights with empty database."""
        reader = FlightReader(empty_db)

        flights = reader.get_recent_flights()

        assert flights == []

        reader.close()


# ============================================================================
# Airlines and Countries Tests
# ============================================================================


class TestGetTopAirlines:
    """Tests for get_top_airlines method."""

    def test_top_airlines_default_limit(self, reader_with_data: FlightReader):
        """Test getting top airlines with default limit."""
        airlines = reader_with_data.get_top_airlines()

        assert len(airlines) <= 10

        # Verify structure
        if airlines:
            assert "airline_code" in airlines[0]
            assert "flight_count" in airlines[0]
            assert "avg_min_distance" in airlines[0]
            assert "avg_max_altitude" in airlines[0]

    def test_top_airlines_custom_limit(self, reader_with_data: FlightReader):
        """Test getting top airlines with custom limit."""
        airlines = reader_with_data.get_top_airlines(limit=3)

        assert len(airlines) <= 3

    def test_top_airlines_sorted_by_count(self, reader_with_data: FlightReader):
        """Test that airlines are sorted by flight count descending."""
        airlines = reader_with_data.get_top_airlines()

        if len(airlines) > 1:
            for i in range(len(airlines) - 1):
                assert airlines[i]["flight_count"] >= airlines[i + 1]["flight_count"]

    def test_top_airlines_extracts_code_correctly(self, reader_with_data: FlightReader):
        """Test that airline code is extracted from callsign."""
        airlines = reader_with_data.get_top_airlines()

        for airline in airlines:
            # Code should be first 3 characters
            assert len(airline["airline_code"]) <= 3

    def test_top_airlines_empty_database(self, empty_db: str):
        """Test top airlines with empty database."""
        reader = FlightReader(empty_db)

        airlines = reader.get_top_airlines()

        assert airlines == []

        reader.close()


class TestGetCountries:
    """Tests for get_countries method."""

    def test_countries_default_limit(self, reader_with_data: FlightReader):
        """Test getting countries with default limit."""
        countries = reader_with_data.get_countries()

        assert len(countries) <= 15

        # Verify structure
        if countries:
            assert "origin_country" in countries[0]
            assert "flight_count" in countries[0]
            assert "avg_min_distance" in countries[0]

    def test_countries_sorted_by_count(self, reader_with_data: FlightReader):
        """Test that countries are sorted by flight count descending."""
        countries = reader_with_data.get_countries()

        if len(countries) > 1:
            for i in range(len(countries) - 1):
                assert countries[i]["flight_count"] >= countries[i + 1]["flight_count"]

    def test_countries_custom_limit(self, reader_with_data: FlightReader):
        """Test getting countries with custom limit."""
        countries = reader_with_data.get_countries(limit=2)

        assert len(countries) <= 2


# ============================================================================
# Distribution Tests
# ============================================================================


class TestGetHourlyDistribution:
    """Tests for get_hourly_distribution method."""

    def test_hourly_distribution_structure(self, reader_with_data: FlightReader):
        """Test hourly distribution returns correct structure."""
        distribution = reader_with_data.get_hourly_distribution()

        # Should have entries for hours that have flights
        assert isinstance(distribution, list)

        for entry in distribution:
            assert "hour" in entry
            assert "flight_count" in entry
            assert 0 <= entry["hour"] <= 23
            assert entry["flight_count"] > 0

    def test_hourly_distribution_sorted_by_hour(self, reader_with_data: FlightReader):
        """Test that distribution is sorted by hour."""
        distribution = reader_with_data.get_hourly_distribution()

        if len(distribution) > 1:
            for i in range(len(distribution) - 1):
                assert distribution[i]["hour"] <= distribution[i + 1]["hour"]

    def test_hourly_distribution_empty_database(self, empty_db: str):
        """Test hourly distribution with empty database."""
        reader = FlightReader(empty_db)

        distribution = reader.get_hourly_distribution()

        assert distribution == []

        reader.close()


class TestGetAltitudeDistribution:
    """Tests for get_altitude_distribution method."""

    def test_altitude_distribution_structure(self, reader_with_data: FlightReader):
        """Test altitude distribution returns correct structure."""
        distribution = reader_with_data.get_altitude_distribution()

        assert isinstance(distribution, list)

        for entry in distribution:
            assert "altitude_range" in entry
            assert "count" in entry
            assert entry["count"] > 0

    def test_altitude_distribution_ranges(self, reader_with_data: FlightReader):
        """Test that altitude ranges are as expected."""
        distribution = reader_with_data.get_altitude_distribution()

        expected_ranges = {
            "0-1000m",
            "1000-3000m",
            "3000-6000m",
            "6000-9000m",
            "9000-12000m",
            "12000m+",
        }

        actual_ranges = {entry["altitude_range"] for entry in distribution}

        # Actual ranges should be subset of expected
        assert actual_ranges.issubset(expected_ranges)

    def test_altitude_distribution_sorted(self, reader_with_data: FlightReader):
        """Test that distribution is sorted by altitude."""
        distribution = reader_with_data.get_altitude_distribution()

        # Define expected order
        expected_order = [
            "0-1000m",
            "1000-3000m",
            "3000-6000m",
            "6000-9000m",
            "9000-12000m",
            "12000m+",
        ]

        actual_order = [entry["altitude_range"] for entry in distribution]

        # Check order is maintained
        last_index = -1
        for range_name in actual_order:
            current_index = expected_order.index(range_name)
            assert current_index > last_index
            last_index = current_index


# ============================================================================
# Closest Flights Tests
# ============================================================================


class TestGetClosestFlights:
    """Tests for get_closest_flights method."""

    def test_closest_flights_default_limit(self, reader_with_data: FlightReader):
        """Test getting closest flights with default limit."""
        flights = reader_with_data.get_closest_flights()

        assert len(flights) <= 10

        # Verify structure
        if flights:
            assert "callsign" in flights[0]
            assert "icao24" in flights[0]
            assert "origin_country" in flights[0]
            assert "min_distance_km" in flights[0]
            assert "latitude" in flights[0]
            assert "longitude" in flights[0]

    def test_closest_flights_sorted_by_distance(self, reader_with_data: FlightReader):
        """Test that flights are sorted by distance ascending."""
        flights = reader_with_data.get_closest_flights()

        if len(flights) > 1:
            for i in range(len(flights) - 1):
                assert (
                    flights[i]["min_distance_km"] <= flights[i + 1]["min_distance_km"]
                )

    def test_closest_flights_custom_limit(self, reader_with_data: FlightReader):
        """Test getting closest flights with custom limit."""
        flights = reader_with_data.get_closest_flights(limit=3)

        assert len(flights) <= 3

    def test_closest_flights_excludes_null_distances(self, empty_db: str):
        """Test that flights without distance are excluded."""
        # Create flight with no distance
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen)
            VALUES ('test123', 'TEST1', 'Germany', '2025-01-01', '2025-01-01')
        """)

        conn.commit()
        conn.close()

        reader = FlightReader(empty_db)
        flights = reader.get_closest_flights()

        assert flights == []

        reader.close()


# ============================================================================
# Daily Stats Tests
# ============================================================================


class TestGetDailyStats:
    """Tests for get_daily_stats method."""

    def test_daily_stats_default_days(self, reader_with_data: FlightReader):
        """Test getting daily stats with default 7 days."""
        stats = reader_with_data.get_daily_stats()

        # Should have up to 7 days of stats
        assert len(stats) <= 7

        # Verify structure
        if stats:
            assert "date" in stats[0]
            assert "flight_count" in stats[0]
            assert "avg_min_distance" in stats[0]
            assert "avg_altitude" in stats[0]

    def test_daily_stats_custom_days(self, reader_with_data: FlightReader):
        """Test getting daily stats with custom number of days."""
        stats = reader_with_data.get_daily_stats(days=3)

        assert len(stats) <= 3

    def test_daily_stats_sorted_descending(self, reader_with_data: FlightReader):
        """Test that stats are sorted by date descending."""
        stats = reader_with_data.get_daily_stats()

        if len(stats) > 1:
            for i in range(len(stats) - 1):
                date1 = datetime.fromisoformat(stats[i]["date"])
                date2 = datetime.fromisoformat(stats[i + 1]["date"])
                assert date1 >= date2

    def test_daily_stats_empty_database(self, empty_db: str):
        """Test daily stats with empty database."""
        reader = FlightReader(empty_db)

        stats = reader.get_daily_stats()

        assert stats == []

        reader.close()


# ============================================================================
# Search and Route Tests
# ============================================================================


class TestSearchFlight:
    """Tests for search_flight method."""

    def test_search_flight_exact_match(self, reader_with_data: FlightReader):
        """Test searching for flight with exact callsign."""
        flights = reader_with_data.search_flight("DLH000")

        assert len(flights) == 1
        assert flights[0]["callsign"] == "DLH000"

    def test_search_flight_partial_match(self, reader_with_data: FlightReader):
        """Test searching with partial callsign."""
        flights = reader_with_data.search_flight("DLH")

        # Should find all DLH flights
        assert len(flights) >= 5

        for flight in flights:
            assert "DLH" in flight["callsign"]

    def test_search_flight_case_insensitive(self, reader_with_data: FlightReader):
        """Test that search is case insensitive."""
        flights_upper = reader_with_data.search_flight("DLH")
        flights_lower = reader_with_data.search_flight("dlh")

        assert len(flights_upper) == len(flights_lower)

    def test_search_flight_includes_statistics(self, reader_with_data: FlightReader):
        """Test that search includes position statistics."""
        flights = reader_with_data.search_flight("DLH000")

        if flights:
            flight = flights[0]
            assert "position_count" in flight
            assert "first_position" in flight
            assert "last_position" in flight

    def test_search_flight_no_results(self, reader_with_data: FlightReader):
        """Test searching for non-existent callsign."""
        flights = reader_with_data.search_flight("NONEXISTENT")

        assert flights == []

    def test_search_flight_sorted_by_time(self, reader_with_data: FlightReader):
        """Test that results are sorted by first_seen descending."""
        flights = reader_with_data.search_flight("DLH")

        if len(flights) > 1:
            for i in range(len(flights) - 1):
                time1 = datetime.fromisoformat(flights[i]["first_seen"])
                time2 = datetime.fromisoformat(flights[i + 1]["first_seen"])
                assert time1 >= time2


class TestGetFlightRoute:
    """Tests for get_flight_route method."""

    def test_get_flight_route_success(self, reader_with_data: FlightReader):
        """Test getting complete route for existing flight."""
        # First get a flight ID
        flights = reader_with_data.get_recent_flights(limit=1)
        assert len(flights) > 0

        flight_id = flights[0]["id"]

        result = reader_with_data.get_flight_route(flight_id)

        assert result is not None
        assert len(result) == 2

        flight_data, positions = result

        # Verify flight data
        assert isinstance(flight_data, dict)
        assert flight_data["id"] == flight_id
        assert "callsign" in flight_data
        assert "icao24" in flight_data

        # Verify positions
        assert isinstance(positions, list)
        assert len(positions) > 0

        for pos in positions:
            assert "latitude" in pos
            assert "longitude" in pos
            assert "timestamp" in pos

    def test_get_flight_route_positions_sorted(self, reader_with_data: FlightReader):
        """Test that positions are sorted by timestamp."""
        flights = reader_with_data.get_recent_flights(limit=1)
        flight_id = flights[0]["id"]

        result = reader_with_data.get_flight_route(flight_id)
        _, positions = result

        if len(positions) > 1:
            for i in range(len(positions) - 1):
                time1 = datetime.fromisoformat(positions[i]["timestamp"])
                time2 = datetime.fromisoformat(positions[i + 1]["timestamp"])
                assert time1 <= time2

    def test_get_flight_route_nonexistent_flight(self, reader_with_data: FlightReader):
        """Test getting route for non-existent flight."""
        result = reader_with_data.get_flight_route(99999)

        assert result is None

    def test_get_flight_route_flight_without_positions(self, empty_db: str):
        """Test getting route for flight with no positions."""
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen)
            VALUES ('test123', 'TEST1', 'Germany', '2025-01-01', '2025-01-01')
        """)

        flight_id = cursor.lastrowid
        conn.commit()
        conn.close()

        reader = FlightReader(empty_db)
        result = reader.get_flight_route(flight_id)

        assert result is not None
        flight_data, positions = result
        assert flight_data["id"] == flight_id
        assert positions == []

        reader.close()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_query_on_closed_connection_raises_error(self, populated_db: str):
        """Test that queries on closed connection raise appropriate error."""
        reader = FlightReader(populated_db)
        reader.close()

        with pytest.raises(sqlite3.ProgrammingError):
            reader.get_overview()

    def test_large_limit_values(self, reader_with_data: FlightReader):
        """Test handling of very large limit values."""
        # Should not crash, just return available data
        flights = reader_with_data.get_recent_flights(limit=1000000)

        assert isinstance(flights, list)
        assert len(flights) <= 15  # Total flights in test data

    def test_zero_limit_returns_empty(self, reader_with_data: FlightReader):
        """Test that zero limit returns empty list."""
        flights = reader_with_data.get_recent_flights(limit=0)

        assert flights == []

    def test_negative_hours_parameter(self, reader_with_data: FlightReader):
        """Test behavior with negative hours parameter."""
        # SQLite will handle negative interval, should return empty or all
        flights = reader_with_data.get_recent_flights(hours=-24)

        assert isinstance(flights, list)

    def test_null_callsign_handling(self, empty_db: str):
        """Test handling of NULL callsigns in queries."""
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen)
            VALUES ('test123', NULL, 'Germany', '2025-01-01', '2025-01-01')
        """)

        conn.commit()
        conn.close()

        reader = FlightReader(empty_db)

        # Should not crash when querying airlines
        airlines = reader.get_top_airlines()
        assert isinstance(airlines, list)

        reader.close()


# ============================================================================
# Integration Tests
# ============================================================================


class TestReaderIntegration:
    """Integration tests for multiple reader operations."""

    def test_complete_analysis_workflow(self, reader_with_data: FlightReader):
        """Test complete workflow of analyzing flight data."""
        # 1. Get overview
        overview = reader_with_data.get_overview()
        assert overview["total_flights"] > 0

        # 2. Get recent flights
        recent = reader_with_data.get_recent_flights()
        assert len(recent) > 0

        # 3. Analyze by airline
        airlines = reader_with_data.get_top_airlines()
        assert len(airlines) > 0

        # 4. Check temporal patterns
        hourly = reader_with_data.get_hourly_distribution()
        assert isinstance(hourly, list)

        # 5. Find closest approach
        closest = reader_with_data.get_closest_flights(limit=1)
        assert len(closest) > 0

        # 6. Get specific flight route
        flight_id = recent[0]["id"]
        route = reader_with_data.get_flight_route(flight_id)
        assert route is not None

    def test_statistics_consistency(self, reader_with_data: FlightReader):
        """Test that statistics are internally consistent."""
        overview = reader_with_data.get_overview()
        recent = reader_with_data.get_recent_flights(hours=24, limit=100)

        # Number of recent flights should not exceed total
        assert len(recent) <= overview["total_flights"]

    def test_multiple_readers_same_database(self, populated_db: str):
        """Test that multiple readers can access same database."""
        reader1 = FlightReader(populated_db)
        reader2 = FlightReader(populated_db)

        overview1 = reader1.get_overview()
        overview2 = reader2.get_overview()

        # Both should see same data
        assert overview1 == overview2

        reader1.close()
        reader2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
