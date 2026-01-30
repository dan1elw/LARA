"""
Heatmap Generator
Creates density heatmaps of flight activity.
"""

from folium import plugins
import sqlite3

from lara.config import Colors


class HeatmapGenerator:
    """
    Generates heatmaps showing flight density.
    """

    def __init__(self, db_path: str, center_lat: float, center_lon: float):
        """
        Initialize heatmap generator.

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

    def generate_traffic_heatmap(self, output_file: str = "traffic_heatmap.html"):
        """
        Generate heatmap of all flight traffic.

        Args:
            output_file: Output HTML filename
        """
        print("🔥 Generating traffic density heatmap...")

        cursor = self.conn.cursor()

        # Get all positions
        cursor.execute("""
            SELECT latitude, longitude, distance_from_home_km
            FROM positions
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)

        # Prepare data for heatmap
        heat_data = []
        for row in cursor.fetchall():
            # Weight by proximity (closer = higher weight)
            weight = 1.0  # / (row['distance_from_home_km'] + 0.1)
            heat_data.append([row["latitude"], row["longitude"], weight])

        print(f"   Plotting {len(heat_data)} positions...")

        # Create base map
        from .map_generator import MapGenerator

        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add heatmap layer
        plugins.HeatMap(
            heat_data,
            min_opacity=0.3,
            max_zoom=18,
            radius=10,
            blur=25,
            gradient=Colors.HEATMAP_GRADIENT,
        ).add_to(map_gen.map)

        # Save
        map_gen.save(output_file)

    def generate_altitude_heatmap(self, output_file: str = "altitude_heatmap.html"):
        """
        Generate heatmap weighted by altitude.

        Args:
            output_file: Output HTML filename
        """
        print("🔥 Generating altitude heatmap...")

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT latitude, longitude, altitude_m
            FROM positions
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL 
            AND altitude_m IS NOT NULL
        """)

        # Weight by altitude (lower = higher weight for noise analysis)
        heat_data = []
        for row in cursor.fetchall():
            weight = 1.0 / (row["altitude_m"] / 1000 + 0.1)  # Inverse altitude
            heat_data.append([row["latitude"], row["longitude"], weight])

        print(f"   Plotting {len(heat_data)} positions...")

        # Create base map
        from .map_generator import MapGenerator

        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add heatmap
        plugins.HeatMap(
            heat_data,
            min_opacity=0.3,
            radius=10,
            blur=25,
            gradient=Colors.HEATMAP_GRADIENT,
        ).add_to(map_gen.map)

        # Save
        map_gen.save(output_file)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
