"""
Map Generator
Creates interactive Folium maps with flight data.
"""

import folium
from folium import plugins
from typing import Dict, Any, List, Tuple, Optional
import json

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
        
        # Add circle showing tracking radius
        # folium.Circle(
        #     radius=25000,  # 25km in meters
        #     location=[self.center_lat, self.center_lon],
        #     popup='Tracking Radius (25km)',
        #     color='crimson',
        #     fill=False,
        #     weight=2,
        #     opacity=0.5
        # ).add_to(m)
        
        return m
    
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
        
        # Add start marker
        # if coords:
        #     folium.CircleMarker(
        #         coords[0],
        #         radius=5,
        #         popup=f"Start: {flight_info.get('callsign')}",
        #         color=color,
        #         fill=True,
        #         fillColor=color,
        #         fillOpacity=0.7
        #     ).add_to(self.map)
    
    def add_position_markers(self, positions: List[Dict[str, Any]]):
        """
        Add individual position markers to the map.
        
        Args:
            positions: List of position dictionaries
        """
        marker_cluster = plugins.MarkerCluster().add_to(self.map)
        
        for pos in positions:
            if not pos.get('latitude') or not pos.get('longitude'):
                continue
            
            altitude = pos.get('altitude_m', 0)
            color = self._get_altitude_color(altitude)
            
            popup_html = f"""
            <b>Altitude:</b> {altitude:.0f} m<br>
            <b>Speed:</b> {pos.get('velocity_ms', 0) * 3.6:.1f} km/h<br>
            <b>Heading:</b> {pos.get('heading', 0):.0f}°<br>
            <b>Distance:</b> {pos.get('distance_from_home_km', 0):.2f} km
            """
            
            # folium.CircleMarker(
            #     [pos['latitude'], pos['longitude']],
            #     radius=MARKER_RADIUS,
            #     popup=popup_html,
            #     color=color,
            #     fill=True,
            #     fillColor=color,
            #     fillOpacity=MARKER_OPACITY
            # ).add_to(marker_cluster)
    
    def add_corridor(self, corridor: Dict[str, Any], rank: int):
        """
        Add a flight corridor to the map.
        
        Args:
            corridor: Corridor data
            rank: Corridor rank (for color coding)
        """
        lat = corridor['center_lat']
        lon = corridor['center_lon']
        
        # Size based on traffic volume
        radius = min(corridor['unique_flights'] * 100, 5000)  # Max 5km
        
        # Color based on rank
        color = self._get_rank_color(rank)
        
        popup_html = f"""
        <b>Corridor #{rank}</b><br>
        <b>Flights:</b> {corridor['unique_flights']}<br>
        <b>Positions:</b> {corridor['total_positions']}<br>
        <b>Avg Altitude:</b> {corridor.get('avg_altitude_m', 0):.0f} m<br>
        <b>Avg Heading:</b> {corridor.get('avg_heading', 0):.0f}°
        """
        
        folium.Circle(
            radius=radius,
            location=[lat, lon],
            popup=popup_html,
            tooltip=f"Corridor #{rank}",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.3,
            weight=2
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
        colors = ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#3498db']
        return colors[min(rank - 1, len(colors) - 1)]
    
    def save(self, filename: str):
        """
        Save map to HTML file.
        
        Args:
            filename: Output filename
        """
        self.map.save(filename)
        print(f"✅ Map saved to: {filename}")
