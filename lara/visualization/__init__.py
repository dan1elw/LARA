"""
LARA Visualization Component

Interactive map visualizations for flight data and analysis results.

Main Classes:
    - MapGenerator: Base interactive map creation with Folium
    - FlightPlotter: Flight path visualization
    - HeatmapGenerator: Density and traffic heatmaps
    - Dashboard: Complete visualization dashboard generation

Example:
    >>> from lara.visualization import Dashboard
    >>> dashboard = Dashboard('data/lara_flights.db', 49.3508, 8.1364)
    >>> dashboard.generate_complete_dashboard()
    >>> dashboard.close()

Map Styles:
    - CartoDB.DarkMatter (default)
    - CartoDB.Positron
    - OpenStreetMap

Features:
    - Dark-themed interactive maps
    - Flight corridor visualization
    - Traffic density heatmaps
    - Altitude-weighted analysis
    - Complete dashboard with landing page
"""

# Main visualization components
from .map_generator import MapGenerator
from .flight_plotter import FlightPlotter
from .heatmap_generator import HeatmapGenerator
from .dashboard import Dashboard

# Utilities
from . import constants

__all__ = [
    # Main classes
    "MapGenerator",
    "FlightPlotter",
    "HeatmapGenerator",
    "Dashboard",
    # Modules
    "constants",
]
