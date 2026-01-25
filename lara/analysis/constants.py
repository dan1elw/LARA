"""
Analysis Constants
"""

# Grid-based clustering
DEFAULT_GRID_SIZE_KM = 5.0
MIN_CORRIDOR_FLIGHTS = 10  # Minimum flights to consider a corridor

# Time analysis
PEAK_HOUR_THRESHOLD = 0.7  # 70% of max hourly traffic
DAYS_FOR_TREND_ANALYSIS = 30

# Pattern detection
MIN_PATTERN_OCCURRENCES = 5
ROUTE_SIMILARITY_THRESHOLD = 0.8  # 80% similarity

# Altitude classifications (meters)
ALTITUDE_CLASSES = {
    'very_low': (0, 1000),
    'low': (1000, 3000),
    'medium': (3000, 6000),
    'high': (6000, 9000),
    'very_high': (9000, 12000),
    'cruise': (12000, float('inf'))
}

# Distance classifications (km)
DISTANCE_CLASSES = {
    'very_close': (0, 5),
    'close': (5, 10),
    'medium': (10, 20),
    'far': (20, 30),
    'very_far': (30, float('inf'))
}
