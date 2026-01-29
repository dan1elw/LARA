"""
Flight Path Plotter
Specialized plotting for individual flights and routes.
"""

import sqlite3
from .map_generator import MapGenerator


class FlightPlotter:
    """
    Plots individual flight paths on maps.
    """

    def __init__(self, db_path: str, center_lat: float, center_lon: float):
        """
        Initialize flight plotter.

        Args:
            db_path: Path to LARA database
            center_lat: Home latitude
            center_lon: Home longitude
        """
        self.db_path = db_path
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def plot_flight(self, flight_id: int, output_file: str):
        """
        Plot a single flight path.

        Args:
            flight_id: Flight ID
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        # Get flight info
        cursor.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
        flight = cursor.fetchone()

        if not flight:
            print(f"❌ Flight {flight_id} not found")
            return

        # Get positions
        cursor.execute(
            """
            SELECT * FROM positions 
            WHERE flight_id = ? 
            ORDER BY timestamp
        """,
            (flight_id,),
        )
        positions = [dict(row) for row in cursor.fetchall()]

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add flight path
        map_gen.add_flight_path(positions, dict(flight))

        # Add position markers
        # map_gen.add_position_markers(positions)

        # Save
        map_gen.save(output_file)

    def plot_recent_flights(
        self, hours: int = 24, output_file: str = "recent_flights.html"
    ):
        """
        Plot all recent flights.

        Args:
            hours: Number of hours to look back
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT f.*, COUNT(p.id) as position_count
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
            WHERE f.first_seen >= datetime('now', ?)
            GROUP BY f.id
            HAVING position_count > 0
        """,
            (f"-{hours} hours",),
        )

        flights = cursor.fetchall()

        print(f"📍 Plotting {len(flights)} recent flights...")

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add each flight
        for flight in flights:
            cursor.execute(
                """
                SELECT * FROM positions 
                WHERE flight_id = ? 
                ORDER BY timestamp
            """,
                (flight["id"],),
            )
            positions = [dict(row) for row in cursor.fetchall()]

            map_gen.add_flight_path(positions, dict(flight))

        # Save
        map_gen.save(output_file)

    def plot_callsign(self, callsign: str, output_file: str):
        """
        Plot all occurrences of a specific callsign.

        Args:
            callsign: Flight callsign
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT * FROM flights 
            WHERE callsign LIKE ?
            ORDER BY first_seen DESC
        """,
            (f"%{callsign}%",),
        )

        flights = cursor.fetchall()

        if not flights:
            print(f"❌ No flights found for callsign: {callsign}")
            return

        print(f"📍 Plotting {len(flights)} flights for {callsign}...")

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add each occurrence
        for flight in flights:
            cursor.execute(
                """
                SELECT * FROM positions 
                WHERE flight_id = ? 
                ORDER BY timestamp
            """,
                (flight["id"],),
            )
            positions = [dict(row) for row in cursor.fetchall()]

            map_gen.add_flight_path(positions, dict(flight))

        # Save
        map_gen.save(output_file)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
