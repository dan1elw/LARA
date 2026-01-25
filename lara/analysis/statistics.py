"""
Statistical Analysis Engine
Provides comprehensive statistical analysis of flight data.
"""

from typing import Dict, Any, List
from .constants import ALTITUDE_CLASSES, DISTANCE_CLASSES, DAYS_FOR_TREND_ANALYSIS


class StatisticsEngine:
    """
    Comprehensive statistical analysis engine.
    """
    
    def __init__(self, db_conn):
        """
        Initialize statistics engine.
        
        Args:
            db_conn: SQLite database connection
        """
        self.conn = db_conn
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get complete statistical overview."""
        return {
            'overview': self._get_overview(),
            'altitude_distribution': self._get_altitude_distribution(),
            'distance_distribution': self._get_distance_distribution(),
            'hourly_pattern': self._get_hourly_pattern(),
            'weekday_pattern': self._get_weekday_pattern()
        }
    
    def _get_overview(self) -> Dict[str, Any]:
        """Get basic overview statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT f.id) as total_flights,
                COUNT(DISTINCT f.icao24) as unique_aircraft,
                COUNT(DISTINCT SUBSTR(f.callsign, 1, 3)) as unique_airlines,
                COUNT(p.id) as total_positions,
                MIN(p.distance_from_home_km) as closest_approach,
                AVG(p.altitude_m) as avg_altitude,
                MIN(f.first_seen) as first_observation,
                MAX(f.last_seen) as last_observation
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
        ''')
        
        row = cursor.fetchone()
        
        return dict(row)
    
    def _get_altitude_distribution(self) -> List[Dict[str, Any]]:
        """Get altitude distribution by class."""
        cursor = self.conn.cursor()
        
        distribution = []
        for class_name, (min_alt, max_alt) in ALTITUDE_CLASSES.items():
            if max_alt == float('inf'):
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM positions
                    WHERE altitude_m >= ?
                ''', (min_alt,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM positions
                    WHERE altitude_m >= ? AND altitude_m < ?
                ''', (min_alt, max_alt))
            
            count = cursor.fetchone()['count']
            distribution.append({
                'class': class_name,
                'min_altitude_m': min_alt,
                'max_altitude_m': max_alt if max_alt != float('inf') else None,
                'count': count
            })
        
        return distribution
    
    def _get_distance_distribution(self) -> List[Dict[str, Any]]:
        """Get distance distribution by class."""
        cursor = self.conn.cursor()
        
        distribution = []
        for class_name, (min_dist, max_dist) in DISTANCE_CLASSES.items():
            if max_dist == float('inf'):
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM positions
                    WHERE distance_from_home_km >= ?
                ''', (min_dist,))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM positions
                    WHERE distance_from_home_km >= ? AND distance_from_home_km < ?
                ''', (min_dist, max_dist))
            
            count = cursor.fetchone()['count']
            distribution.append({
                'class': class_name,
                'min_distance_km': min_dist,
                'max_distance_km': max_dist if max_dist != float('inf') else None,
                'count': count
            })
        
        return distribution
    
    def _get_hourly_pattern(self) -> List[Dict[str, Any]]:
        """Get hourly traffic pattern."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CAST(strftime('%H', first_seen) AS INTEGER) as hour,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_distance,
                AVG(max_altitude_m) as avg_altitude
            FROM flights
            GROUP BY hour
            ORDER BY hour
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_weekday_pattern(self) -> List[Dict[str, Any]]:
        """Get weekday traffic pattern."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CASE CAST(strftime('%w', first_seen) AS INTEGER)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as weekday,
                COUNT(*) as flight_count
            FROM flights
            GROUP BY strftime('%w', first_seen)
            ORDER BY CAST(strftime('%w', first_seen) AS INTEGER)
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def analyze_temporal_patterns(self, days: int = DAYS_FOR_TREND_ANALYSIS) -> Dict[str, Any]:
        """Analyze temporal trends."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                DATE(first_seen) as date,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_distance
            FROM flights
            WHERE first_seen >= date('now', ?)
            GROUP BY DATE(first_seen)
            ORDER BY date
        ''', (f'-{days} days',))
        
        daily_data = [dict(row) for row in cursor.fetchall()]
        
        return {
            'days_analyzed': days,
            'daily_trends': daily_data,
            'avg_daily_flights': sum(d['flight_count'] for d in daily_data) / len(daily_data) if daily_data else 0
        }
    
    def analyze_airlines(self) -> Dict[str, Any]:
        """Analyze airline patterns."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                SUBSTR(callsign, 1, 3) as airline_code,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_min_distance,
                AVG(max_altitude_m) as avg_altitude,
                MIN(min_distance_km) as closest_approach
            FROM flights
            WHERE callsign IS NOT NULL AND callsign != ''
            GROUP BY airline_code
            HAVING flight_count > 1
            ORDER BY flight_count DESC
            LIMIT 30
        ''')
        
        return {
            'top_airlines': [dict(row) for row in cursor.fetchall()]
        }
