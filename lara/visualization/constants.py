"""
Visualization Constants
"""

# Map configuration
DEFAULT_MAP_STYLE = 'CartoDB.DarkMatter'
DEFAULT_ZOOM = 10
MAP_TILE_URLS = {
    'CartoDB.DarkMatter': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    'CartoDB.Positron': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    'OpenStreetMap': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
}

# Color schemes
ALTITUDE_COLORS = {
    'very_low': '#e74c3c',      # Red
    'low': '#e67e22',           # Orange
    'medium': '#f39c12',        # Yellow
    'high': '#2ecc71',          # Green
    'very_high': '#3498db',     # Blue
    'cruise': '#9b59b6'         # Purple
}

HEATMAP_GRADIENT = {
    0.0: '#313695',
    0.25: '#4575b4',
    0.5: '#fee090',
    0.75: '#f46d43',
    1.0: '#a50026'
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
