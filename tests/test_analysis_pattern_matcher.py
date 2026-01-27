"""
Tests for pattern matching.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.analysis.pattern_matcher import PatternMatcher


@pytest.fixture
def pattern_db():
    """Create database with recurring flights."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables with COMPLETE schema
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY,
            icao24 TEXT,
            callsign TEXT,
            origin_country TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            min_distance_km REAL,
            max_altitude_m REAL
        )
    """)

    # Insert recurring flights
    base_time = datetime.now()
    for i in range(10):
        time = (base_time + timedelta(days=i)).isoformat()
        cursor.execute(
            """
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen, min_distance_km, max_altitude_m)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            ("abc123", "DLH123", "Germany", time, time, 5.0, 10000),
        )

    # Insert some other flights
    for i in range(5):
        time = (base_time + timedelta(days=i)).isoformat()
        cursor.execute(
            """
            INSERT INTO flights 
            (icao24, callsign, origin_country, first_seen, last_seen, min_distance_km, max_altitude_m)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (f"xyz{i}", f"AFR{i}", "France", time, time, 10.0, 9000),
        )

    conn.commit()

    yield conn

    conn.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    def test_init(self, pattern_db):
        """Test pattern matcher initialization."""
        matcher = PatternMatcher(pattern_db)
        assert matcher.conn is not None

    def test_find_patterns(self, pattern_db):
        """Test complete pattern finding."""
        matcher = PatternMatcher(pattern_db)
        result = matcher.find_patterns()

        assert "recurring_flights" in result
        assert "schedules" in result
        assert "route_variations" in result

    def test_find_recurring_flights(self, pattern_db):
        """Test recurring flight detection."""
        matcher = PatternMatcher(pattern_db)
        recurring = matcher._find_recurring_flights()

        assert len(recurring) > 0
        # DLH123 should be found (10 occurrences)
        dlh_flights = [f for f in recurring if f["callsign"] == "DLH123"]
        assert len(dlh_flights) > 0
        assert dlh_flights[0]["occurrences"] == 10

    def test_find_schedules(self, pattern_db):
        """Test schedule detection."""
        matcher = PatternMatcher(pattern_db)
        schedules = matcher._find_schedules()

        # Should find some schedules
        assert isinstance(schedules, list)

    def test_route_variations(self, pattern_db):
        """Test route variation detection."""
        matcher = PatternMatcher(pattern_db)
        variations = matcher._find_route_variations()

        assert "high_variation_routes" in variations
        assert "count" in variations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
