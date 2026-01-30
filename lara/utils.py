"""
LARA Utility Functions
Common utility functions for distance calculations and data processing.
"""

from math import radians, sin, cos, sqrt, atan2, degrees
from typing import Tuple
from .config import Constants


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance between two points using Haversine formula.

    The Haversine formula calculates the shortest distance over the earth's
    surface, giving an "as-the-crow-flies" distance between two points
    (ignoring any hills they fly over, of course!).

    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees

    Returns:
        Distance in kilometers

    Example:
        >>> haversine_distance(49.3508, 8.1364, 49.4, 8.2)
        7.23
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return Constants.EARTH_RADIUS_KM * c


def perpendicular_distance(lat: float, lon: float, line) -> float:
    """
    Calculate perpendicular distance from point to line.

    Uses cross product formula to find the shortest distance
    from a point to a line segment. This is an approximation
    that works well for small distances.

    Args:
        lat: Point latitude
        lon: Point longitude
        line: Line segment

    Returns:
        Distance in kilometers
    """
    # Simple approximation using cross product
    # For small distances this is sufficiently accurate

    # Vector from line start to point
    dx1 = lon - line.start_lon
    dy1 = lat - line.start_lat

    # Vector along line
    dx2 = line.end_lon - line.start_lon
    dy2 = line.end_lat - line.start_lat

    # Normalize line vector
    line_length = sqrt(dx2**2 + dy2**2)
    if line_length < 1e-10:
        return haversine_distance(lat, lon, line.start_lat, line.start_lon)

    dx2 /= line_length
    dy2 /= line_length

    # Calculate perpendicular distance (cross product magnitude)
    cross = abs(dx1 * dy2 - dy1 * dx2)

    # Convert to kilometers (approximate)
    return cross * Constants.KM_PER_DEGREE_LAT  # degrees to km


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing (direction) from point 1 to point 2.

    Returns the initial bearing (forward azimuth) from the first
    point to the second point. Note that the bearing may change
    along a great circle path.

    Args:
        lat1, lon1: Start point (degrees)
        lat2, lon2: End point (degrees)

    Returns:
        Bearing in degrees (0-360, where 0/360=North, 90=East, 180=South, 270=West)
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1

    x = sin(dlon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)

    bearing = atan2(x, y)
    bearing = degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing


def get_bounding_box(
    lat: float, lon: float, radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box coordinates for a given point and radius.

    Args:
        lat: Center latitude in degrees
        lon: Center longitude in degrees
        radius_km: Radius in kilometers

    Returns:
        Tuple of (lat_min, lon_min, lat_max, lon_max)

    Example:
        >>> get_bounding_box(49.3508, 8.1364, 50)
        (48.9008, 7.5164, 49.8008, 8.7564)
    """
    # Calculate latitude delta (constant)
    lat_delta = radius_km / Constants.KM_PER_DEGREE_LAT

    # Calculate longitude delta (varies by latitude)
    lon_delta = radius_km / (Constants.KM_PER_DEGREE_LAT * cos(radians(lat)))

    return (
        lat - lat_delta,  # lat_min
        lon - lon_delta,  # lon_min
        lat + lat_delta,  # lat_max
        lon + lon_delta,  # lon_max
    )


def format_altitude(altitude_m: float, include_feet: bool = True) -> str:
    """
    Format altitude with optional feet conversion.

    Args:
        altitude_m: Altitude in meters
        include_feet: Whether to include feet conversion

    Returns:
        Formatted altitude string

    Example:
        >>> format_altitude(10000)
        '10000 m (32808 ft)'
    """
    if altitude_m is None:
        return "N/A"

    if include_feet:
        feet = altitude_m * Constants.METERS_TO_FEET
        return f"{altitude_m:.0f} m ({feet:.0f} ft)"

    return f"{altitude_m:.0f} m"


def format_speed(velocity_ms: float, unit: str = "kmh") -> str:
    """
    Format speed in various units.

    Args:
        velocity_ms: Velocity in meters per second
        unit: Output unit ('kmh', 'ms', 'knots')

    Returns:
        Formatted speed string

    Example:
        >>> format_speed(100, 'kmh')
        '360.0 km/h'
    """
    if velocity_ms is None:
        return "N/A"

    if unit == "kmh":
        return f"{velocity_ms * Constants.MS_TO_KMH:.1f} km/h"
    elif unit == "knots":
        return f"{velocity_ms * 1.94384:.1f} knots"
    else:  # ms
        return f"{velocity_ms:.1f} m/s"


def format_duration(seconds: int) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds is None or seconds < 0:
        return "N/A"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude coordinates.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees

    Returns:
        True if coordinates are valid

    Example:
        >>> validate_coordinates(49.3508, 8.1364)
        True
        >>> validate_coordinates(100, 200)
        False
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def parse_state_vector(state: list) -> dict:
    """
    Parse OpenSky Network state vector into dictionary.

    Args:
        state: State vector from OpenSky API

    Returns:
        Dictionary with parsed flight data

    OpenSky state vector format:
        [0] icao24 - unique ICAO 24-bit address
        [1] callsign - callsign
        [2] origin_country - country name
        [3] time_position - Unix timestamp
        [4] last_contact - Unix timestamp
        [5] longitude
        [6] latitude
        [7] baro_altitude - barometric altitude in meters
        [8] on_ground - boolean
        [9] velocity - m/s
        [10] true_track - degrees
        [11] vertical_rate - m/s
        [12] sensors - sensor IDs
        [13] geo_altitude - geometric altitude in meters
        [14] squawk - transponder code
        [15] spi - special position indicator
        [16] position_source - position source (0=ADS-B, 1=ASTERIX, 2=MLAT)
    """
    return {
        "icao24": state[0],
        "callsign": state[1].strip() if state[1] else None,
        "origin_country": state[2],
        "time_position": state[3],
        "last_contact": state[4],
        "longitude": state[5],
        "latitude": state[6],
        "baro_altitude": state[7],
        "on_ground": state[8],
        "velocity": state[9],
        "true_track": state[10],
        "vertical_rate": state[11],
        "geo_altitude": state[13],
        "squawk": state[14] if len(state) > 14 else None,
    }
