"""
LARA Constants
Global constants used throughout the application.
"""

# Database constants
DEFAULT_DB_PATH = "data/lara_flights.db"

# API constants
OPENSKY_API_URL = "https://opensky-network.org/api/states/all"
DEFAULT_API_TIMEOUT = 10  # seconds

# Tracking constants
DEFAULT_RADIUS_KM = 35
DEFAULT_UPDATE_INTERVAL = 10  # seconds
MIN_UPDATE_INTERVAL = 10  # OpenSky rate limit

# Earth radius for distance calculations
EARTH_RADIUS_KM = 6371

# Conversion factors
METERS_TO_FEET = 3.28084
MS_TO_KMH = 3.6
KM_PER_DEGREE_LAT = 111.0

# Flight tracking
FLIGHT_SESSION_TIMEOUT_MINUTES = 30

# Altitude ranges for distribution analysis (in meters)
ALTITUDE_RANGES = [
    (0, 1000, "0-1000m"),
    (1000, 3000, "1000-3000m"),
    (3000, 6000, "3000-6000m"),
    (6000, 9000, "6000-9000m"),
    (9000, 12000, "9000-12000m"),
    (12000, float("inf"), "12000m+"),
]

# Database schema version
SCHEMA_VERSION = "1.0.0"
