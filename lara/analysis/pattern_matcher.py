"""
Flight Pattern Detection
Identifies recurring flight routes and patterns.
"""

from typing import Dict, Any, List
from lara.config import Settings


class PatternMatcher:
    """
    Detects recurring flight patterns and routes.
    """

    def __init__(self, db_conn):
        """
        Initialize pattern matcher.

        Args:
            db_conn: SQLite database connection
        """
        self.conn = db_conn

    def find_patterns(self) -> Dict[str, Any]:
        """
        Find recurring flight patterns.

        Returns:
            Dictionary with pattern analysis
        """
        patterns = {}

        # Find recurring flights (same callsign)
        patterns["recurring_flights"] = self._find_recurring_flights()

        # Find regular schedules
        patterns["schedules"] = self._find_schedules()

        # Find route variations
        patterns["route_variations"] = self._find_route_variations()

        return patterns

    def _find_recurring_flights(self) -> List[Dict[str, Any]]:
        """Find flights that appear multiple times."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT 
                callsign,
                COUNT(*) as occurrence_count,
                AVG(min_distance_km) as avg_min_distance,
                AVG(max_altitude_m) as avg_altitude,
                MIN(first_seen) as first_occurrence,
                MAX(last_seen) as last_occurrence
            FROM flights
            WHERE callsign IS NOT NULL AND callsign != ''
            GROUP BY callsign
            HAVING occurrence_count >= ?
            ORDER BY occurrence_count DESC
            LIMIT 50
        """,
            (Settings.MIN_PATTERN_OCCURRENCES,),
        )

        recurring = []
        for row in cursor.fetchall():
            recurring.append(
                {
                    "callsign": row["callsign"],
                    "occurrences": row["occurrence_count"],
                    "avg_min_distance_km": row["avg_min_distance"],
                    "avg_altitude_m": row["avg_altitude"],
                    "first_seen": row["first_occurrence"],
                    "last_seen": row["last_occurrence"],
                }
            )

        print(f"Found {len(recurring)} recurring flights")
        for flight in recurring[:10]:
            print(f"  {flight['callsign']:8s}: {flight['occurrences']:3d} times")

        return recurring

    def _find_schedules(self) -> List[Dict[str, Any]]:
        """Find regular flight schedules."""
        cursor = self.conn.cursor()

        # Group by callsign and hour
        cursor.execute("""
            SELECT 
                callsign,
                CAST(strftime('%H', first_seen) AS INTEGER) as hour,
                COUNT(*) as count
            FROM flights
            WHERE callsign IS NOT NULL AND callsign != ''
            GROUP BY callsign, hour
            HAVING count >= 3
            ORDER BY count DESC
            LIMIT 50
        """)

        schedules = []
        for row in cursor.fetchall():
            schedules.append(
                {
                    "callsign": row["callsign"],
                    "hour": row["hour"],
                    "frequency": row["count"],
                }
            )

        print(f"Found {len(schedules)} regular schedules")

        return schedules

    def _find_route_variations(self) -> Dict[str, Any]:
        """Find variations in routes for same callsign."""
        cursor = self.conn.cursor()

        # For each recurring flight, check distance variation
        cursor.execute("""
            SELECT 
                callsign,
                COUNT(*) as flights,
                AVG(min_distance_km) as avg_distance,
                MIN(min_distance_km) as min_distance,
                MAX(min_distance_km) as max_distance,
                (MAX(min_distance_km) - MIN(min_distance_km)) as distance_variation
            FROM flights
            WHERE callsign IS NOT NULL
            GROUP BY callsign
            HAVING flights >= 5
            ORDER BY distance_variation DESC
            LIMIT 20
        """)

        variations = []
        for row in cursor.fetchall():
            if row["distance_variation"] > 5:  # More than 5km variation
                variations.append(
                    {
                        "callsign": row["callsign"],
                        "flights": row["flights"],
                        "avg_distance_km": row["avg_distance"],
                        "variation_km": row["distance_variation"],
                    }
                )

        return {"high_variation_routes": variations, "count": len(variations)}
