"""
Flight Corridor Detection
Identifies common linear flight paths using directional clustering and path analysis.

This module detects flight corridors by:
1. Grouping flight segments by direction (heading) and spatial proximity
2. Fitting linear corridors to grouped segments
3. Validating corridor quality (linearity, consistency)
4. Ranking corridors by usage (unique flights)

A corridor is defined as a linear path segment where multiple flights follow
similar routes in the same general direction.
"""

from typing import Dict, Any, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from collections import defaultdict
import math

# Type alias for database row (since we can't import sqlite3.Row type)
DbRow = Any


@dataclass
class Position:
    """Represents a single position point from a flight."""

    latitude: float
    longitude: float
    altitude_m: Optional[float]
    heading: Optional[float]
    flight_id: int
    callsign: Optional[str]


@dataclass
class LineSegment:
    """Represents a fitted line segment (potential corridor)."""

    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    heading: float
    length_km: float

    def midpoint(self) -> Tuple[float, float]:
        """Calculate midpoint of line segment."""
        return (
            (self.start_lat + self.end_lat) / 2,
            (self.start_lon + self.end_lon) / 2,
        )


@dataclass
class Corridor:
    """Represents a detected flight corridor."""

    rank: int
    center_lat: float
    center_lon: float
    heading: float
    length_km: float
    width_km: float
    unique_flights: int
    total_positions: int
    avg_altitude_m: float
    linearity_score: float  # 0-1, higher is more linear
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float


class CorridorDetector:
    """
    Detects common flight corridors using directional clustering and path fitting.

    Algorithm:
    1. Load all position data with heading information
    2. Group positions into directional segments (similar heading, close proximity)
    3. For each segment group, fit a linear corridor
    4. Validate corridor quality (linearity, consistency)
    5. Rank corridors by unique flight count

    Configuration:
        HEADING_TOLERANCE_DEG: Positions within ±30° are considered same direction
        PROXIMITY_THRESHOLD_KM: Positions within 2km can belong to same corridor
        MIN_CORRIDOR_LENGTH_KM: Minimum corridor length to be valid
        MIN_LINEARITY_SCORE: Minimum linearity score (0-1) for quality filter
    """

    # Configuration constants
    HEADING_TOLERANCE_DEG: float = 30.0  # Positions within ±30° are same direction
    PROXIMITY_THRESHOLD_KM: float = (
        10.0  # Positions within 10km can belong to same corridor
    )
    MIN_CORRIDOR_LENGTH_KM: float = 3.0  # Minimum corridor length (lowered to 3km)
    MIN_LINEARITY_SCORE: float = 0.5  # Minimum linearity (0-1, lowered to 0.5)

    def __init__(self, db_conn: Any) -> None:
        """
        Initialize corridor detector.

        Args:
            db_conn: SQLite database connection with row_factory set
        """
        self.conn = db_conn

    def detect_corridors(
        self,
        min_flights: int = 10,
        heading_tolerance: float = HEADING_TOLERANCE_DEG,
        proximity_km: float = PROXIMITY_THRESHOLD_KM,
    ) -> Dict[str, Any]:
        """
        Detect flight corridors using directional path analysis.

        This method:
        1. Loads position data with heading information
        2. Groups positions by direction and proximity
        3. Fits linear corridors to each group
        4. Filters by quality metrics (linearity, length)
        5. Ranks corridors by unique flight count

        Args:
            min_flights: Minimum unique flights to qualify as corridor (default: 10)
            heading_tolerance: Heading tolerance in degrees ± (default: 30°)
            proximity_km: Maximum distance for positions to group in km (default: 2km)

        Returns:
            Dictionary containing:
                - total_corridors: Number of detected corridors
                - corridors: List of corridor dictionaries (top 50)
                - parameters: Detection parameters used

        Example:
            >>> detector = CorridorDetector(db_conn)
            >>> result = detector.detect_corridors(min_flights=5)
            >>> print(f"Found {result['total_corridors']} corridors")
        """
        print(f"\n🔍 Detecting flight corridors...")
        print(
            f"   Parameters: min_flights={min_flights}, "
            f"heading_tolerance=±{heading_tolerance}°, proximity={proximity_km}km"
        )

        # Step 1: Load position data
        positions = self._load_positions()
        print(f"   Loaded {len(positions)} positions")

        if len(positions) < min_flights * 2:
            print(f"   ⚠️  Insufficient data for corridor detection")
            return {
                "total_corridors": 0,
                "corridors": [],
                "parameters": {
                    "min_flights": min_flights,
                    "heading_tolerance": heading_tolerance,
                    "proximity_km": proximity_km,
                },
            }

        # Step 2: Group positions by direction and proximity
        directional_groups = self._group_by_direction_and_proximity(
            positions, heading_tolerance, proximity_km
        )
        print(f"   Found {len(directional_groups)} directional groups")

        # Step 3: Fit corridors to each group
        corridors: List[Corridor] = []
        for group_positions in directional_groups:
            corridor = self._fit_corridor(group_positions)
            if corridor and corridor.unique_flights >= min_flights:
                corridors.append(corridor)

        # Step 4: Filter by quality
        quality_corridors = [
            c
            for c in corridors
            if c.linearity_score >= self.MIN_LINEARITY_SCORE
            and c.length_km >= self.MIN_CORRIDOR_LENGTH_KM
        ]

        print(
            f"   Fitted {len(corridors)} corridors, "
            f"{len(quality_corridors)} passed quality filters"
        )

        # Step 5: Sort and rank
        quality_corridors.sort(key=lambda x: x.unique_flights, reverse=True)
        for i, corridor in enumerate(quality_corridors, 1):
            corridor.rank = i

        # Display top 10
        print(f"\n📊 Top Corridors:")
        for corridor in quality_corridors[:10]:
            print(
                f"  #{corridor.rank:2d}: "
                f"Heading {corridor.heading:>3.0f}°, "
                f"Length {corridor.length_km:>5.1f}km, "
                f"{corridor.unique_flights:>3d} flights, "
                f"Linearity {corridor.linearity_score:.2f}"
            )

        return {
            "total_corridors": len(quality_corridors),
            "corridors": [self._corridor_to_dict(c) for c in quality_corridors[:50]],
            "parameters": {
                "min_flights": min_flights,
                "heading_tolerance": heading_tolerance,
                "proximity_km": proximity_km,
                "min_linearity": self.MIN_LINEARITY_SCORE,
                "min_length_km": self.MIN_CORRIDOR_LENGTH_KM,
            },
        }

    def _load_positions(self) -> List[Position]:
        """
        Load all position data with required fields.

        Loads positions that have:
        - Valid latitude/longitude
        - Valid heading information
        - Associated flight information

        Returns:
            List of Position objects
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT 
                p.latitude, 
                p.longitude, 
                p.altitude_m,
                p.heading,
                p.flight_id,
                f.callsign
            FROM positions p
            JOIN flights f ON p.flight_id = f.id
            WHERE p.latitude IS NOT NULL 
            AND p.longitude IS NOT NULL
            AND p.heading IS NOT NULL
        """)

        positions: List[Position] = []
        for row in cursor.fetchall():
            positions.append(
                Position(
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    altitude_m=row["altitude_m"],
                    heading=row["heading"],
                    flight_id=row["flight_id"],
                    callsign=row["callsign"],
                )
            )

        return positions

    def _group_by_direction_and_proximity(
        self, positions: List[Position], heading_tolerance: float, proximity_km: float
    ) -> List[List[Position]]:
        """
        Group positions into directional segments.

        Positions are grouped if they:
        1. Have similar headings (within tolerance)
        2. Are spatially close (within proximity threshold)

        Algorithm:
        1. Bin positions by heading (10° bins)
        2. Within each bin, cluster spatially using proximity threshold
        3. Validate heading consistency within each cluster

        Args:
            positions: All positions to group
            heading_tolerance: Heading tolerance in degrees (±)
            proximity_km: Maximum distance between positions in group (km)

        Returns:
            List of position groups, each representing a potential corridor
        """
        # First, create heading bins (every 10 degrees)
        heading_bins: Dict[int, List[Position]] = defaultdict(list)
        bin_size = 10.0

        for pos in positions:
            if pos.heading is None:
                continue
            bin_idx = int(pos.heading / bin_size)
            heading_bins[bin_idx].append(pos)

        # Now cluster spatially within each heading bin
        groups: List[List[Position]] = []

        for bin_positions in heading_bins.values():
            if len(bin_positions) < 3:
                continue

            # Spatial clustering using simple proximity
            ungrouped = bin_positions.copy()

            while ungrouped:
                # Start new group with first ungrouped position
                seed = ungrouped.pop(0)
                group = [seed]

                # Find all positions close to this group
                i = 0
                while i < len(ungrouped):
                    pos = ungrouped[i]

                    # Check if close to any position in current group
                    is_close = any(
                        self._haversine_distance(
                            pos.latitude, pos.longitude, g.latitude, g.longitude
                        )
                        < proximity_km
                        for g in group
                    )

                    # Check heading similarity
                    heading_diff = min(
                        abs(pos.heading - seed.heading),
                        360 - abs(pos.heading - seed.heading),
                    )

                    if is_close and heading_diff < heading_tolerance:
                        group.append(ungrouped.pop(i))
                    else:
                        i += 1

                if len(group) >= 3:  # Minimum 3 positions for a group
                    groups.append(group)

        return groups

    def _fit_corridor(self, positions: List[Position]) -> Optional[Corridor]:
        """
        Fit a linear corridor to a group of positions.

        Uses least-squares line fitting to find the best linear corridor
        through the position group. Calculates corridor metrics including:
        - Center point
        - Heading/direction
        - Length and width
        - Linearity score (how well positions fit the line)
        - Unique flight count

        Args:
            positions: Group of positions to fit

        Returns:
            Corridor object or None if fitting fails
        """
        if len(positions) < 3:
            return None

        # Extract coordinates
        lats = [p.latitude for p in positions]
        lons = [p.longitude for p in positions]
        alts = [p.altitude_m for p in positions if p.altitude_m is not None]

        # Get unique flights
        unique_flights = len(set(p.flight_id for p in positions))

        # Fit line using least squares
        line = self._fit_line_least_squares(lats, lons)
        if line is None:
            return None

        # Calculate corridor metrics
        center_lat, center_lon = line.midpoint()
        avg_altitude = sum(alts) / len(alts) if alts else 0.0

        # Calculate perpendicular distances for width estimation
        distances = [
            self._perpendicular_distance(p.latitude, p.longitude, line)
            for p in positions
        ]
        width_km = 2 * (sum(distances) / len(distances))  # Average distance * 2

        # Calculate linearity score (how well points fit the line)
        max_dist = max(distances) if distances else 0.0
        linearity = 1.0 - min(max_dist / (line.length_km / 2 + 0.001), 1.0)

        return Corridor(
            rank=0,  # Will be set later
            center_lat=center_lat,
            center_lon=center_lon,
            heading=line.heading,
            length_km=line.length_km,
            width_km=width_km,
            unique_flights=unique_flights,
            total_positions=len(positions),
            avg_altitude_m=avg_altitude,
            linearity_score=linearity,
            start_lat=line.start_lat,
            start_lon=line.start_lon,
            end_lat=line.end_lat,
            end_lon=line.end_lon,
        )

    def _fit_line_least_squares(
        self, lats: List[float], lons: List[float]
    ) -> Optional[LineSegment]:
        """
        Fit a line to points using least squares regression.

        Finds the best-fit line through a set of points using
        the standard least squares method: minimizing the sum
        of squared residuals.

        Args:
            lats: Latitude values
            lons: Longitude values

        Returns:
            LineSegment or None if fitting fails
        """
        if len(lats) < 2:
            return None

        # Calculate means
        mean_lat = sum(lats) / len(lats)
        mean_lon = sum(lons) / len(lons)

        # Calculate variance in each direction
        lat_variance = sum((lat - mean_lat) ** 2 for lat in lats) / len(lats)
        lon_variance = sum((lon - mean_lon) ** 2 for lon in lons) / len(lons)

        # Determine which direction has more variation
        # If corridor is more vertical (N-S), latitude varies more - use it as independent
        # If corridor is more horizontal (E-W), longitude varies more - use it as independent
        use_lat_as_independent = lat_variance > lon_variance

        if use_lat_as_independent:
            # Corridor is more N-S: fit lon = f(lat)
            numerator = sum(
                (lats[i] - mean_lat) * (lons[i] - mean_lon) for i in range(len(lats))
            )
            denominator = sum((lats[i] - mean_lat) ** 2 for i in range(len(lats)))

            if abs(denominator) < 1e-10:
                # Horizontal line
                start_lat = mean_lat
                end_lat = mean_lat
                start_lon = min(lons)
                end_lon = max(lons)
            else:
                slope = numerator / denominator
                intercept = mean_lon - slope * mean_lat

                # Use min/max latitude for endpoints
                min_lat = min(lats)
                max_lat = max(lats)
                start_lat = min_lat
                end_lat = max_lat
                start_lon = slope * min_lat + intercept
                end_lon = slope * max_lat + intercept
        else:
            # Corridor is more E-W: fit lat = f(lon)
            numerator = sum(
                (lons[i] - mean_lon) * (lats[i] - mean_lat) for i in range(len(lats))
            )
            denominator = sum((lons[i] - mean_lon) ** 2 for i in range(len(lons)))

            if abs(denominator) < 1e-10:
                # Vertical line
                start_lat = min(lats)
                end_lat = max(lats)
                start_lon = mean_lon
                end_lon = mean_lon
            else:
                slope = numerator / denominator
                intercept = mean_lat - slope * mean_lon

                # Use min/max longitude for endpoints
                min_lon = min(lons)
                max_lon = max(lons)
                start_lon = min_lon
                end_lon = max_lon
                start_lat = slope * min_lon + intercept
                end_lat = slope * max_lon + intercept

        # Calculate heading
        heading = self._calculate_bearing(start_lat, start_lon, end_lat, end_lon)

        # Calculate length
        length = self._haversine_distance(start_lat, start_lon, end_lat, end_lon)

        return LineSegment(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            heading=heading,
            length_km=length,
        )

    def _perpendicular_distance(
        self, lat: float, lon: float, line: LineSegment
    ) -> float:
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
        line_length = math.sqrt(dx2**2 + dy2**2)
        if line_length < 1e-10:
            return self._haversine_distance(lat, lon, line.start_lat, line.start_lon)

        dx2 /= line_length
        dy2 /= line_length

        # Calculate perpendicular distance (cross product magnitude)
        cross = abs(dx1 * dy2 - dy1 * dx2)

        # Convert to kilometers (approximate)
        return cross * 111.0  # degrees to km

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate great circle distance between two points using Haversine formula.

        The Haversine formula calculates the shortest distance over the earth's
        surface, giving an "as-the-crow-flies" distance between two points
        (ignoring any hills they fly over, of course!).

        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)

        Returns:
            Distance in kilometers

        Example:
            >>> distance = self._haversine_distance(49.35, 8.14, 49.36, 8.15)
            >>> print(f"{distance:.2f} km")
        """
        R = 6371  # Earth radius in km

        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_bearing(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
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
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        dlon = lon2 - lon1

        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
            lat2
        ) * math.cos(dlon)

        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360

        return bearing

    def _corridor_to_dict(self, corridor: Corridor) -> Dict[str, Any]:
        """
        Convert Corridor object to dictionary for serialization.

        Creates a dictionary representation suitable for JSON serialization
        and API responses.

        Args:
            corridor: Corridor object

        Returns:
            Dictionary representation with all corridor attributes
        """
        return {
            "rank": corridor.rank,
            "center_lat": corridor.center_lat,
            "center_lon": corridor.center_lon,
            "heading": corridor.heading,
            "length_km": corridor.length_km,
            "width_km": corridor.width_km,
            "unique_flights": corridor.unique_flights,
            "total_positions": corridor.total_positions,
            "avg_altitude_m": corridor.avg_altitude_m,
            "linearity_score": corridor.linearity_score,
            "start_lat": corridor.start_lat,
            "start_lon": corridor.start_lon,
            "end_lat": corridor.end_lat,
            "end_lon": corridor.end_lon,
            # Legacy field for compatibility
            "avg_heading": corridor.heading,
        }
