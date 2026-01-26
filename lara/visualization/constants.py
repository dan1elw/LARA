"""
Visualization Constants
"""

# Map configuration
DEFAULT_MAP_STYLE = 'CartoDB.Positron'
DEFAULT_ZOOM = 10
MAP_TILE_URLS = {
    'CartoDB.DarkMatter': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    'CartoDB.Positron': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    'OpenStreetMap': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
}

# Color schemes
ALTITUDE_COLORS = {
    'very_low':  '#ff3b3b',
    'low':       '#ff7a18',
    'medium':    '#f5e663',
    'high':      '#00e5a8',
    'very_high': '#00b4ff',
    'cruise':    '#7c3aed'
}

HEATMAP_GRADIENT = {    # Neon Plasma
    0.0: '#120018',
    0.25: '#6a00ff',
    0.5: '#ff2fd2',
    0.75: '#ff9f1c',
    1.0: '#fff200'
}

# Flight path colors
FLIGHT_PATH_COLOR = '#3498db'
FLIGHT_PATH_WEIGHT = 2
FLIGHT_PATH_OPACITY = 0.6

# Marker styles
MARKER_RADIUS = 8
MARKER_OPACITY = 0.7
MARKER_FILL_OPACITY = 0.5

# Corridor visualization
CORRIDOR_OPACITY = 0.3
CORRIDOR_BORDER_WEIGHT = 2
