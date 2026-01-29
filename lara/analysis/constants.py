"""
Analysis Constants
"""

# Corridor analysis
HEADING_TOLERANCE_DEG: float = 20.0  # Positions within ±20° are same direction
PROXIMITY_THRESHOLD_KM: float = 10.0  # Positions within 10km can belong to same corridor
MIN_CORRIDOR_LENGTH_KM: float = 3.0  # Minimum corridor length (lowered to 3km)
MIN_LINEARITY_SCORE: float = 0.3  # Minimum linearity (0-1, lowered to 0.5)
MIN_FLIGHTS_FOR_CORRIDOR: int = 15  # Minimum unique flights to qualify as corridor

# Time analysis
PEAK_HOUR_THRESHOLD = 0.7  # 70% of max hourly traffic
DAYS_FOR_TREND_ANALYSIS = 30

# Pattern detection
MIN_PATTERN_OCCURRENCES = 5
ROUTE_SIMILARITY_THRESHOLD = 0.8  # 80% similarity

# Altitude classifications (meters)
ALTITUDE_CLASSES = {
    "very_low": (0, 1000),
    "low": (1000, 3000),
    "medium": (3000, 6000),
    "high": (6000, 9000),
    "very_high": (9000, 12000),
    "cruise": (12000, float("inf")),
}

# Distance classifications (km)
DISTANCE_CLASSES = {
    "very_close": (0, 5),
    "close": (5, 10),
    "medium": (10, 20),
    "far": (20, 30),
    "very_far": (30, float("inf")),
}
