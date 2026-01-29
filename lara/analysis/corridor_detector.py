"""
Flight Corridor Detection
Identifies common flight paths using spatial clustering.
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict
import math

from .constants import DEFAULT_GRID_SIZE_KM, MIN_CORRIDOR_FLIGHTS


class CorridorDetector:
    """
    Detects common flight corridors using grid-based clustering.
    """

    def __init__(self, db_conn):
        """
        Initialize corridor detector.

        Args:
            db_conn: SQLite database connection
        """
        self.conn = db_conn

    def detect_corridors(
        self,
        grid_size_km: float = DEFAULT_GRID_SIZE_KM,
        min_flights: int = MIN_CORRIDOR_FLIGHTS,
    ) -> Dict[str, Any]:
        """
        Detect flight corridors using grid-based spatial clustering.

        Args:
            grid_size_km: Size of grid cells in kilometers
            min_flights: Minimum number of flights to qualify as corridor

        Returns:
            Dictionary with corridor data
        """
        cursor = self.conn.cursor()

        # Get all positions
        cursor.execute("""
            SELECT 
                p.latitude, 
                p.longitude, 
                p.altitude_m,
                p.heading,
                f.callsign
            FROM positions p
            JOIN flights f ON p.flight_id = f.id
            WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        """)

        # Grid-based clustering
        grid = defaultdict(
            lambda: {"count": 0, "altitudes": [], "headings": [], "flights": set()}
        )

        for row in cursor.fetchall():
            lat, lon = row["latitude"], row["longitude"]
            alt = row["altitude_m"]
            heading = row["heading"]
            callsign = row["callsign"]

            # Calculate grid cell
            grid_lat, grid_lon = self._get_grid_cell(lat, lon, grid_size_km)
            key = (grid_lat, grid_lon)

            grid[key]["count"] += 1
            if alt:
                grid[key]["altitudes"].append(alt)
            if heading:
                grid[key]["headings"].append(heading)
            if callsign:
                grid[key]["flights"].add(callsign)

        # Filter and sort corridors
        corridors = []
        for coords, data in grid.items():
            if len(data["flights"]) >= min_flights:
                avg_alt = (
                    sum(data["altitudes"]) / len(data["altitudes"])
                    if data["altitudes"]
                    else 0
                )
                avg_heading = (
                    self._circular_mean(data["headings"]) if data["headings"] else None
                )

                corridor = {
                    "center_lat": coords[0],
                    "center_lon": coords[1],
                    "unique_flights": len(data["flights"]),
                    "total_positions": data["count"],
                    "avg_altitude_m": avg_alt,
                    "avg_heading": avg_heading,
                }
                corridors.append(corridor)

        # Sort by number of unique flights
        corridors.sort(key=lambda x: x["unique_flights"], reverse=True)

        # Add rank
        for i, corridor in enumerate(corridors, 1):
            corridor["rank"] = i

        print(f"Found {len(corridors)} corridors (min {min_flights} flights)")

        # Display top 10
        for corridor in corridors[:10]:
            print(
                f"  #{corridor['rank']:2d}: ({corridor['center_lat']:.4f}, {corridor['center_lon']:.4f}) - "
                f"{corridor['unique_flights']} flights, {corridor['total_positions']} positions"
            )

        return {
            "grid_size_km": grid_size_km,
            "min_flights": min_flights,
            "total_corridors": len(corridors),
            "corridors": corridors[:50],  # Return top 50
        }

    def _get_grid_cell(
        self, lat: float, lon: float, grid_size_km: float
    ) -> Tuple[float, float]:
        """Round coordinates to grid cell center."""
        # 1 degree latitude ≈ 111 km
        lat_grid = round(lat / (grid_size_km / 111.0)) * (grid_size_km / 111.0)
        lon_grid = round(lon / (grid_size_km / 111.0)) * (grid_size_km / 111.0)
        return (lat_grid, lon_grid)

    def _circular_mean(self, angles: List[float]) -> float:
        """Calculate circular mean for headings (0-360°)."""
        if not angles:
            return None

        sin_sum = sum(math.sin(math.radians(a)) for a in angles)
        cos_sum = sum(math.cos(math.radians(a)) for a in angles)

        mean_rad = math.atan2(sin_sum, cos_sum)
        mean_deg = math.degrees(mean_rad)

        return mean_deg if mean_deg >= 0 else mean_deg + 360
