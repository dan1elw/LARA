"""
LARA Flight Reader
Query and analyze stored flight data.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .database import FlightDatabase
from .utils import format_altitude, format_speed, format_duration


class FlightReader:
    """Read and query LARA flight database."""
    
    def __init__(self, db_path: str):
        """
        Initialize reader.
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_overview(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT f.id) as total_flights,
                COUNT(DISTINCT f.icao24) as unique_aircraft,
                COUNT(p.id) as total_positions,
                AVG(p.altitude_m) as avg_altitude,
                MIN(p.distance_from_home_km) as closest_approach,
                MIN(f.first_seen) as first_observation,
                MAX(f.last_seen) as last_observation
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
        ''')
        
        row = cursor.fetchone()
        
        return {
            'total_flights': row['total_flights'] or 0,
            'unique_aircraft': row['unique_aircraft'] or 0,
            'total_positions': row['total_positions'] or 0,
            'avg_altitude_m': row['avg_altitude'] or 0,
            'closest_approach_km': row['closest_approach'],
            'first_observation': row['first_observation'],
            'last_observation': row['last_observation']
        }
    
    def get_recent_flights(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent flights."""
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT 
                f.*,
                CAST((julianday(f.last_seen) - julianday(f.first_seen)) * 24 * 60 AS INTEGER) as duration_minutes
            FROM flights f
            WHERE f.first_seen >= ?
            ORDER BY f.first_seen DESC
            LIMIT ?
        ''', (cutoff, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_top_airlines(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common airlines/callsigns."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                SUBSTR(callsign, 1, 3) as airline_code,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_min_distance,
                AVG(max_altitude_m) as avg_max_altitude
            FROM flights
            WHERE callsign IS NOT NULL AND callsign != ''
            GROUP BY airline_code
            ORDER BY flight_count DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_countries(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get flights by country."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                origin_country,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_min_distance
            FROM flights
            GROUP BY origin_country
            ORDER BY flight_count DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_hourly_distribution(self) -> List[Dict[str, Any]]:
        """Get flight distribution by hour of day."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CAST(strftime('%H', first_seen) AS INTEGER) as hour,
                COUNT(*) as flight_count
            FROM flights
            GROUP BY hour
            ORDER BY hour
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_altitude_distribution(self) -> List[Dict[str, Any]]:
        """Get altitude distribution."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN altitude_m < 1000 THEN '0-1000m'
                    WHEN altitude_m < 3000 THEN '1000-3000m'
                    WHEN altitude_m < 6000 THEN '3000-6000m'
                    WHEN altitude_m < 9000 THEN '6000-9000m'
                    WHEN altitude_m < 12000 THEN '9000-12000m'
                    ELSE '12000m+'
                END as altitude_range,
                COUNT(*) as count
            FROM positions
            WHERE altitude_m IS NOT NULL
            GROUP BY altitude_range
            ORDER BY 
                CASE 
                    WHEN altitude_m < 1000 THEN 1
                    WHEN altitude_m < 3000 THEN 2
                    WHEN altitude_m < 6000 THEN 3
                    WHEN altitude_m < 9000 THEN 4
                    WHEN altitude_m < 12000 THEN 5
                    ELSE 6
                END
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_closest_flights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get flights that came closest to home."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                f.callsign,
                f.icao24,
                f.origin_country,
                f.first_seen,
                f.min_distance_km,
                f.min_altitude_m,
                p.latitude,
                p.longitude
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id 
                AND p.distance_from_home_km = f.min_distance_km
            WHERE f.min_distance_km IS NOT NULL
            ORDER BY f.min_distance_km ASC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                DATE(first_seen) as date,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_min_distance,
                AVG(max_altitude_m) as avg_altitude
            FROM flights
            WHERE first_seen >= date('now', ?)
            GROUP BY DATE(first_seen)
            ORDER BY date DESC
        ''', (f'-{days} days',))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_flight(self, callsign: str) -> List[Dict[str, Any]]:
        """Search for specific flight by callsign."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                f.*,
                COUNT(p.id) as position_count,
                MIN(p.timestamp) as first_position,
                MAX(p.timestamp) as last_position
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
            WHERE f.callsign LIKE ?
            GROUP BY f.id
            ORDER BY f.first_seen DESC
        ''', (f'%{callsign}%',))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_flight_route(self, flight_id: int) -> Optional[tuple]:
        """
        Get complete route for a specific flight.
        
        Returns:
            Tuple of (flight_data, positions_list)
        """
        cursor = self.conn.cursor()
        
        # Get flight info
        cursor.execute('SELECT * FROM flights WHERE id = ?', (flight_id,))
        flight = cursor.fetchone()
        
        if not flight:
            return None
        
        # Get positions
        cursor.execute('''
            SELECT * FROM positions 
            WHERE flight_id = ? 
            ORDER BY timestamp
        ''', (flight_id,))
        
        positions = cursor.fetchall()
        
        return (dict(flight), [dict(p) for p in positions])
