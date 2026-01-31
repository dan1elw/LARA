"""
Map Generator
Creates interactive Folium maps with flight data.

Updated to properly visualize linear flight corridors instead of circular clusters.
"""

import folium
from typing import Dict, Any, List

from lara.config import Settings, Colors

MAP_TILE_URLS = {
    "CartoDB.DarkMatter": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "CartoDB.Positron": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    "OpenStreetMap": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
}


class MapGenerator:
    """
    Generates interactive maps using Folium.

    Supports visualization of:
    - Flight paths (individual trajectories)
    - Flight corridors (linear routes with multiple flights)
    - Position markers
    - Traffic density heatmaps
    """

    def __init__(
        self,
        center_lat: float,
        center_lon: float,
        zoom: int = Settings.DEFAULT_ZOOM,
        style: str = Settings.DEFAULT_MAP_STYLE,
    ):
        """
        Initialize map generator.

        Args:
            center_lat: Center latitude (home location)
            center_lon: Center longitude (home location)
            zoom: Initial zoom level (default: 10)
            style: Map style/theme (default: CartoDB.DarkMatter)
        """
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom = zoom
        self.style = style

        # Create base map
        self.map = self._create_base_map()

    def _create_base_map(self) -> folium.Map:
        """Create base Folium map with dark theme."""

        if self.style in MAP_TILE_URLS:
            tiles = MAP_TILE_URLS[self.style]
        else:
            tiles = self.style

        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom,
            tiles=tiles,
            attr="LARA Flight Visualization",
        )

        # Add home location marker
        folium.Marker(
            [self.center_lat, self.center_lon],
            popup="Home Location",
            tooltip="Your Location",
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
        ).add_to(m)

        return m

    def add_flight_path(
        self, positions: List[Dict[str, Any]], flight_info: Dict[str, Any]
    ):
        """
        Add a flight path to the map.

        Args:
            positions: List of position dictionaries with lat/lon/altitude
            flight_info: Flight metadata (callsign, icao24, etc.)
        """
        if not positions:
            return

        # Extract coordinates
        coords = [
            [p["latitude"], p["longitude"]]
            for p in positions
            if p["latitude"] and p["longitude"]
        ]

        if not coords:
            return

        # Filter out None values before calculating average
        altitudes = [p["altitude_m"] for p in positions if p.get("altitude_m") is not None]
        avg_altitude = sum(altitudes) / len(altitudes) if altitudes else 0.0
        # Color by altitude
        color = self._get_altitude_color(avg_altitude)

        # Create polyline for flight path
        folium.PolyLine(
            coords,
            color=color,
            weight=Settings.FLIGHT_PATH_WEIGHT,
            opacity=Settings.FLIGHT_PATH_OPACITY,
            popup=f"{flight_info.get('callsign', 'Unknown')} - {avg_altitude:.0f}m",
            tooltip=flight_info.get("callsign", "Unknown"),
        ).add_to(self.map)

    def add_corridor(self, corridor: Dict[str, Any], rank: int):
        """
        Add a linear flight corridor to the map.

        Draws corridors as line segments with width indicators,
        showing the actual linear path rather than circular clusters.

        Args:
            corridor: Corridor data dictionary with:
                - start_lat, start_lon: Start point
                - end_lat, end_lon: End point
                - heading: Direction in degrees
                - length_km: Corridor length
                - width_km: Corridor width
                - unique_flights: Number of flights using corridor
                - linearity_score: Quality metric (0-1)
            rank: Corridor rank (for color coding and priority)
        """
        # Extract corridor geometry
        start_lat = corridor.get("start_lat", corridor["center_lat"])
        start_lon = corridor.get("start_lon", corridor["center_lon"])
        end_lat = corridor.get("end_lat", corridor["center_lat"])
        end_lon = corridor.get("end_lon", corridor["center_lon"])

        # Color based on rank
        color = self._get_rank_color(rank)

        # Calculate line weight based on traffic volume
        # More flights = thicker line
        base_weight = 3
        weight = min(base_weight + (corridor["unique_flights"] // 5), 12)

        # Create main corridor line
        corridor_line = folium.PolyLine(
            locations=[[start_lat, start_lon], [end_lat, end_lon]],
            color=color,
            weight=weight,
            opacity=0.8,
            popup=self._create_corridor_popup(corridor, rank),
            tooltip=f"Corridor #{rank} ({corridor['unique_flights']} flights)",
        )
        corridor_line.add_to(self.map)

        # Add width indicator (parallel lines)
        width_lines = self._create_width_indicators(
            start_lat, start_lon, end_lat, end_lon, corridor.get("width_km", 2.0), color
        )
        for line in width_lines:
            line.add_to(self.map)

    def _create_corridor_popup(self, corridor: Dict[str, Any], rank: int) -> str:
        """
        Create HTML popup for corridor visualization.

        Args:
            corridor: Corridor data
            rank: Corridor rank

        Returns:
            HTML string for popup
        """
        linearity = corridor.get("linearity_score", 0.0)
        linearity_quality = (
            "Excellent" if linearity > 0.8 else "Good" if linearity > 0.6 else "Fair"
        )

        html = f"""
        <div style='font-family: Arial; min-width: 200px;'>
            <h4 style='margin: 0 0 10px 0; color: #667eea;'>
                ✈️ Corridor #{rank}
            </h4>
            <table style='width: 100%; border-collapse: collapse;'>
                <tr><td><b>Direction:</b></td><td>{corridor['heading']:.0f}°</td></tr>
                <tr><td><b>Length:</b></td><td>{corridor['length_km']:.1f} km</td></tr>
                <tr><td><b>Width:</b></td><td>{corridor.get('width_km', 0):.1f} km</td></tr>
                <tr><td><b>Flights:</b></td><td>{corridor['unique_flights']}</td></tr>
                <tr><td><b>Positions:</b></td><td>{corridor['total_positions']}</td></tr>
                <tr><td><b>Avg Altitude:</b></td><td>{corridor.get('avg_altitude_m', 0):.0f} m</td></tr>
                <tr><td><b>Quality:</b></td><td>{linearity_quality} ({linearity:.2f})</td></tr>
            </table>
        </div>
        """
        return html

    def _create_width_indicators(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        width_km: float,
        color: str,
    ) -> List[folium.PolyLine]:
        """
        Create parallel lines to indicate corridor width.

        Args:
            start_lat, start_lon: Start point
            end_lat, end_lon: End point
            width_km: Corridor width in km
            color: Line color

        Returns:
            List of polylines representing width boundaries
        """
        import math

        # Calculate perpendicular offset (half width on each side)
        offset_km = width_km / 4  # Quarter width for visual clarity

        # Calculate bearing
        lat1, lon1, lat2, lon2 = map(
            math.radians, [start_lat, start_lon, end_lat, end_lon]
        )
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
            lat2
        ) * math.cos(dlon)
        bearing = math.atan2(x, y)

        # Perpendicular bearing (±90°)
        perp_bearing_1 = bearing + math.pi / 2
        perp_bearing_2 = bearing - math.pi / 2

        R = 6371  # Earth radius in km

        # Calculate offset points
        def offset_point(lat, lon, bearing, distance):
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)

            lat_new = math.asin(
                math.sin(lat_rad) * math.cos(distance / R)
                + math.cos(lat_rad) * math.sin(distance / R) * math.cos(bearing)
            )
            lon_new = lon_rad + math.atan2(
                math.sin(bearing) * math.sin(distance / R) * math.cos(lat_rad),
                math.cos(distance / R) - math.sin(lat_rad) * math.sin(lat_new),
            )

            return math.degrees(lat_new), math.degrees(lon_new)

        # Create parallel lines
        start_offset_1 = offset_point(start_lat, start_lon, perp_bearing_1, offset_km)
        end_offset_1 = offset_point(end_lat, end_lon, perp_bearing_1, offset_km)

        start_offset_2 = offset_point(start_lat, start_lon, perp_bearing_2, offset_km)
        end_offset_2 = offset_point(end_lat, end_lon, perp_bearing_2, offset_km)

        lines = []

        # Add dashed boundary lines
        line1 = folium.PolyLine(
            locations=[start_offset_1, end_offset_1],
            color=color,
            weight=1,
            opacity=0.4,
            dash_array="5, 5",
        )
        lines.append(line1)

        line2 = folium.PolyLine(
            locations=[start_offset_2, end_offset_2],
            color=color,
            weight=1,
            opacity=0.4,
            dash_array="5, 5",
        )
        lines.append(line2)

        return lines

    def _get_altitude_color(self, altitude_m: float) -> str:
        """
        Get color based on altitude.

        Args:
            altitude_m: Altitude in meters

        Returns:
            Color hex code
        """
        if altitude_m < 1000:
            return Colors.ALTITUDE_COLORS["very_low"]
        elif altitude_m < 3000:
            return Colors.ALTITUDE_COLORS["low"]
        elif altitude_m < 6000:
            return Colors.ALTITUDE_COLORS["medium"]
        elif altitude_m < 9000:
            return Colors.ALTITUDE_COLORS["high"]
        elif altitude_m < 12000:
            return Colors.ALTITUDE_COLORS["very_high"]
        else:
            return Colors.ALTITUDE_COLORS["cruise"]

    def _get_rank_color(self, rank: int) -> str:
        """
        Get color based on corridor rank.

        Top-ranked corridors get more prominent colors.

        Args:
            rank: Corridor rank (1 = highest traffic)

        Returns:
            Color hex code
        """
        return Colors.RANKED_COLORS[min(rank - 1, len(Colors.RANKED_COLORS) - 1)]

    def save(self, filename: str):
        """
        Save map to HTML file.

        Args:
            filename: Output filename (should end in .html)
        """
        self.map.save(filename)

        # Modify HTML file to include title and favicon
        with open(filename, "r", encoding="utf-8") as f:
            html_content = f.read()
        line1 = "<title>LARA Map</title>"
        line2 = '<link rel="icon" href="../docu/icon.ico">'
        insert = "<head>\n    " + line1 + "\n    " + line2
        html_content = html_content.replace("<head>", insert, 1)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ Map saved to: {filename}")
