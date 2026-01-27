"""
Map Generator
Creates interactive Folium maps with flight data.
"""

import folium
from folium import plugins
from typing import Dict, Any, List, Tuple, Optional
import json
import math

from .constants import (
    DEFAULT_MAP_STYLE, DEFAULT_ZOOM, MAP_TILE_URLS,
    ALTITUDE_COLORS, FLIGHT_PATH_COLOR, FLIGHT_PATH_WEIGHT,
    FLIGHT_PATH_OPACITY, MARKER_RADIUS, MARKER_OPACITY
)


class MapGenerator:
    """
    Generates interactive maps using Folium.
    """
    
    def __init__(self, center_lat: float, center_lon: float, 
                 zoom: int = DEFAULT_ZOOM,
                 style: str = DEFAULT_MAP_STYLE):
        """
        Initialize map generator.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            zoom: Initial zoom level
            style: Map style/theme
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
            attr='LARA Flight Visualization'
        )
        
        # Add home location marker
        folium.Marker(
            [self.center_lat, self.center_lon],
            popup='Home Location',
            tooltip='Your Location',
            icon=folium.Icon(color='red', icon='home', prefix='fa')
        ).add_to(m)
        
        return m
    
    def add_corridor_linear(self, corridor: Dict[str, Any], rank: int):
        """
        Add a bidirectional flight corridor to the map.
        
        Args:
            corridor: Corridor data with corridor_points
            rank: Corridor rank (for color coding)
        """
        if not corridor.get('corridor_points'):
            return
        
        # Get corridor path points
        path_points = corridor['corridor_points']
        
        if len(path_points) < 2:
            return
        
        # Color based on rank
        color = self._get_rank_color(rank)
        
        # Create corridor popup (without direction since it's bidirectional)
        popup_html = f"""
        <b>Corridor #{rank}</b><br>
        <b>Flights:</b> {corridor['unique_flights']}<br>
        <b>Positions:</b> {corridor['total_positions']}<br>
        <b>Avg Altitude:</b> {corridor.get('avg_altitude', 0):.0f} m ({corridor.get('avg_altitude', 0) * 3.28084:.0f} ft)<br>
        <b>Sample Flights:</b> {', '.join(corridor.get('sample_callsigns', [])[:3])}
        """
        
        # Main corridor line (thick)
        folium.PolyLine(
            path_points,
            color=color,
            weight=8,
            opacity=0.7,
            popup=popup_html,
            tooltip=f"Corridor #{rank}: {corridor['unique_flights']} flights"
        ).add_to(self.map)
        
        # Add buffer zone (translucent polygon showing corridor width)
        buffer_points = self._create_buffer_polygon(path_points, buffer_km=3.0)
        
        if buffer_points and len(buffer_points) > 2:
            folium.Polygon(
                buffer_points,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.15,
                weight=1,
                opacity=0.25
            ).add_to(self.map)
    
    def _create_buffer_polygon(self, path_points: List[Tuple[float, float]], 
                               buffer_km: float) -> List[Tuple[float, float]]:
        """
        Create a simple buffer polygon around a path.
        
        Args:
            path_points: List of (lat, lon) points
            buffer_km: Buffer distance in kilometers
        
        Returns:
            List of polygon points
        """
        if len(path_points) < 2:
            return path_points
        
        buffer_deg = buffer_km / 111.0  # Approximate conversion
        
        # Create offset points on both sides
        left_points = []
        right_points = []
        
        for i in range(len(path_points)):
            lat, lon = path_points[i]
            
            # Calculate perpendicular direction
            if i < len(path_points) - 1:
                next_lat, next_lon = path_points[i + 1]
                dx = next_lon - lon
                dy = next_lat - lat
            else:
                prev_lat, prev_lon = path_points[i - 1]
                dx = lon - prev_lon
                dy = lat - prev_lat
            
            # Perpendicular vector (rotated 90 degrees)
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x = -dy / length * buffer_deg
                perp_y = dx / length * buffer_deg
                
                left_points.append((lat + perp_y, lon + perp_x))
                right_points.append((lat - perp_y, lon - perp_x))
            else:
                left_points.append((lat, lon))
                right_points.append((lat, lon))
        
        # Create closed polygon
        return left_points + list(reversed(right_points))
    
    def add_flight_path(self, positions: List[Dict[str, Any]], 
                       flight_info: Dict[str, Any]):
        """
        Add a flight path to the map.
        
        Args:
            positions: List of position dictionaries
            flight_info: Flight metadata
        """
        if not positions:
            return
        
        # Extract coordinates
        coords = [[p['latitude'], p['longitude']] for p in positions 
                 if p['latitude'] and p['longitude']]
        
        if not coords:
            return
        
        # Color by altitude
        avg_altitude = sum(p.get('altitude_m', 0) for p in positions) / len(positions)
        color = self._get_altitude_color(avg_altitude)
        
        # Create polyline for flight path
        folium.PolyLine(
            coords,
            color=color,
            weight=FLIGHT_PATH_WEIGHT,
            opacity=FLIGHT_PATH_OPACITY,
            popup=f"{flight_info.get('callsign', 'Unknown')} - {avg_altitude:.0f}m",
            tooltip=flight_info.get('callsign', 'Unknown')
        ).add_to(self.map)
    
    def _get_altitude_color(self, altitude_m: float) -> str:
        """Get color based on altitude."""
        if altitude_m < 1000:
            return ALTITUDE_COLORS['very_low']
        elif altitude_m < 3000:
            return ALTITUDE_COLORS['low']
        elif altitude_m < 6000:
            return ALTITUDE_COLORS['medium']
        elif altitude_m < 9000:
            return ALTITUDE_COLORS['high']
        elif altitude_m < 12000:
            return ALTITUDE_COLORS['very_high']
        else:
            return ALTITUDE_COLORS['cruise']
    
    def _get_rank_color(self, rank: int) -> str:
        """Get color based on corridor rank."""
        colors = ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#3498db',
                 '#9b59b6', '#1abc9c', '#34495e']
        return colors[min(rank - 1, len(colors) - 1)]
    
    def save(self, filename: str):
        """
        Save map to HTML file.
        
        Args:
            filename: Output filename
        """
        self.map.save(filename)

        # Modify HTML file to include title and favicon
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        line1 = '<title>LARA Map</title>'
        line2 = '<link rel="icon" href="../docu/icon.ico">'
        insert = "<head>\n    " + line1 + "\n    " + line2
        html_content = html_content.replace("<head>", insert, 1)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✅ Map saved to: {filename}")
