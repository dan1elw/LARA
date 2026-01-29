"""
Tests for flight plotter.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.visualization.flight_plotter import FlightPlotter


@pytest.fixture
def plotter_db():
    """Create sample database for plotter testing."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY,
            callsign TEXT,
            first_seen TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            timestamp TIMESTAMP
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO flights (id, callsign, first_seen)
        VALUES (1, 'TEST123', datetime('now'))
    """)

    for i in range(5):
        cursor.execute(
            """
            INSERT INTO positions (flight_id, latitude, longitude, altitude_m, timestamp)
            VALUES (1, ?, ?, 10000, datetime('now'))
        """,
            (49.35 + i * 0.01, 8.14 + i * 0.01),
        )

    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestFlightPlotter:
    """Tests for FlightPlotter class."""

    def test_init(self, plotter_db):
        """Test plotter initialization."""
        plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)
        assert plotter.db_path == plotter_db
        assert plotter.conn is not None
        plotter.close()

    def test_plot_flight(self, plotter_db):
        """Test plotting single flight."""
        plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            plotter.plot_flight(1, temp_path)
            assert Path(temp_path).exists()
        finally:
            plotter.close()
            Path(temp_path).unlink(missing_ok=True)

    def test_plot_nonexistent_flight(self, plotter_db, capsys):
        """Test plotting nonexistent flight."""
        plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)

        plotter.plot_flight(999, "dummy.html")
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

        plotter.close()
