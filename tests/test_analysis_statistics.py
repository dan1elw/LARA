"""
Tests for statistics engine.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.analysis.statistics import StatisticsEngine


@pytest.fixture
def stats_db():
    """Create database with statistical test data."""
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
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            min_distance_km REAL,
            max_altitude_m REAL,
            min_altitude_m REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            altitude_m REAL,
            distance_from_home_km REAL
        )
    """)

    # Insert test data with various altitudes and distances
    for i in range(20):
        cursor.execute(
            """
            INSERT INTO flights (icao24, callsign, first_seen, last_seen, min_distance_km, max_altitude_m)
            VALUES (?, ?, datetime('now', ?), datetime('now', ?), ?, ?)
        """,
            (f"test{i}", f"TST{i}", f"-{i} hours", f"-{i} hours", i * 2.0, 10000),
        )
        flight_id = cursor.lastrowid

        # Add positions at different altitudes
        for alt in [1000, 5000, 10000]:
            cursor.execute(
                """
                INSERT INTO positions (flight_id, altitude_m, distance_from_home_km)
                VALUES (?, ?, ?)
            """,
                (flight_id, alt, i * 2.0),
            )

    conn.commit()

    yield conn

    conn.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestStatisticsEngine:
    """Tests for StatisticsEngine class."""

    def test_init(self, stats_db):
        """Test statistics engine initialization."""
        engine = StatisticsEngine(stats_db)
        assert engine.conn is not None

    def test_get_comprehensive_stats(self, stats_db):
        """Test comprehensive statistics."""
        engine = StatisticsEngine(stats_db)
        stats = engine.get_comprehensive_stats()

        assert "overview" in stats
        assert "altitude_distribution" in stats
        assert "distance_distribution" in stats
        assert "hourly_pattern" in stats
        assert "weekday_pattern" in stats

    def test_overview(self, stats_db):
        """Test overview statistics."""
        engine = StatisticsEngine(stats_db)
        overview = engine._get_overview()

        assert overview["total_flights"] == 20
        assert overview["total_positions"] == 60  # 20 flights * 3 positions

    def test_altitude_distribution(self, stats_db):
        """Test altitude distribution."""
        engine = StatisticsEngine(stats_db)
        dist = engine._get_altitude_distribution()

        assert len(dist) > 0
        # Should have entries for different altitude classes
        classes = [d["class"] for d in dist]
        assert "very_low" in classes
        assert "medium" in classes

    def test_distance_distribution(self, stats_db):
        """Test distance distribution."""
        engine = StatisticsEngine(stats_db)
        dist = engine._get_distance_distribution()

        assert len(dist) > 0
        # Should have entries for different distance classes
        classes = [d["class"] for d in dist]
        assert "very_close" in classes

    def test_hourly_pattern(self, stats_db):
        """Test hourly pattern analysis."""
        engine = StatisticsEngine(stats_db)
        pattern = engine._get_hourly_pattern()

        # Should return data for hours
        assert isinstance(pattern, list)

    def test_temporal_patterns(self, stats_db):
        """Test temporal pattern analysis."""
        engine = StatisticsEngine(stats_db)
        result = engine.analyze_temporal_patterns(days=7)

        assert "daily_trends" in result
        assert "avg_daily_flights" in result

    def test_airline_analysis(self, stats_db):
        """Test airline analysis."""
        engine = StatisticsEngine(stats_db)
        result = engine.analyze_airlines()

        assert "top_airlines" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
