"""
LARA Database Management
SQLite database operations for storing and querying flight data.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from .constants import FLIGHT_SESSION_TIMEOUT_MINUTES


class FlightDatabase:
    """Manages SQLite database for flight data storage."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_data_directory()
        self.init_database()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """Initialize database with required tables and indexes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for unique flights (one entry per flight session)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                icao24 TEXT NOT NULL,
                callsign TEXT,
                origin_country TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                min_distance_km REAL,
                max_altitude_m REAL,
                min_altitude_m REAL,
                avg_velocity_ms REAL,
                position_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for position updates (tracking route over time)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                latitude REAL,
                longitude REAL,
                altitude_m REAL,
                geo_altitude_m REAL,
                velocity_ms REAL,
                heading REAL,
                vertical_rate_ms REAL,
                distance_from_home_km REAL,
                on_ground BOOLEAN,
                squawk TEXT,
                FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE CASCADE
            )
        ''')
        
        # Table for daily statistics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_flights INTEGER,
                total_positions INTEGER,
                avg_altitude_m REAL,
                min_distance_km REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flights_icao24 ON flights(icao24)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flights_first_seen ON flights(first_seen)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_flight_id ON positions(flight_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions(timestamp)')
        
        conn.commit()
        conn.close()
    
    def get_or_create_flight(self, icao24: str, callsign: Optional[str], 
                            origin_country: str, timestamp: str) -> int:
        """
        Get existing flight or create new one.
        
        A flight is considered the same if it has the same ICAO24 and callsign,
        and was last seen within FLIGHT_SESSION_TIMEOUT_MINUTES.
        
        Args:
            icao24: Aircraft ICAO 24-bit address
            callsign: Flight callsign
            origin_country: Country of origin
            timestamp: Current timestamp
        
        Returns:
            Flight ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Look for active flight (seen within timeout period)
        cursor.execute(f'''
            SELECT id FROM flights 
            WHERE icao24 = ? AND callsign = ?
            AND datetime(last_seen) > datetime(?, '-{FLIGHT_SESSION_TIMEOUT_MINUTES} minutes')
            ORDER BY last_seen DESC LIMIT 1
        ''', (icao24, callsign, timestamp))
        
        result = cursor.fetchone()
        
        if result:
            flight_id = result[0]
            # Update last_seen
            cursor.execute('UPDATE flights SET last_seen = ? WHERE id = ?', 
                         (timestamp, flight_id))
        else:
            # Create new flight entry
            cursor.execute('''
                INSERT INTO flights (icao24, callsign, origin_country, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
            ''', (icao24, callsign, origin_country, timestamp, timestamp))
            flight_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return flight_id
    
    def add_position(self, flight_id: int, state_data: Dict[str, Any], 
                    distance_km: float, timestamp: str):
        """
        Add position update for a flight.
        
        Args:
            flight_id: Flight ID
            state_data: Parsed state vector data
            distance_km: Distance from home location
            timestamp: Position timestamp
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert position
        cursor.execute('''
            INSERT INTO positions (
                flight_id, timestamp, latitude, longitude, altitude_m, geo_altitude_m,
                velocity_ms, heading, vertical_rate_ms, distance_from_home_km, 
                on_ground, squawk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            flight_id, timestamp,
            state_data.get('latitude'),
            state_data.get('longitude'),
            state_data.get('baro_altitude'),
            state_data.get('geo_altitude'),
            state_data.get('velocity'),
            state_data.get('true_track'),
            state_data.get('vertical_rate'),
            distance_km,
            state_data.get('on_ground'),
            state_data.get('squawk')
        ))
        
        # Update flight statistics
        altitude = state_data.get('baro_altitude') or state_data.get('geo_altitude')
        
        if altitude:
            cursor.execute('''
                UPDATE flights SET
                    position_count = position_count + 1,
                    min_distance_km = COALESCE(MIN(min_distance_km, ?), ?),
                    max_altitude_m = COALESCE(MAX(max_altitude_m, ?), ?),
                    min_altitude_m = COALESCE(MIN(min_altitude_m, ?), ?)
                WHERE id = ?
            ''', (distance_km, distance_km, 
                  altitude, altitude,
                  altitude, altitude,
                  flight_id))
        else:
            cursor.execute('''
                UPDATE flights SET
                    position_count = position_count + 1,
                    min_distance_km = COALESCE(MIN(min_distance_km, ?), ?)
                WHERE id = ?
            ''', (distance_km, distance_km, flight_id))
        
        conn.commit()
        conn.close()
    
    def update_daily_stats(self, date: str):
        """
        Update daily statistics for a given date.
        
        Args:
            date: Date in ISO format (YYYY-MM-DD)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats 
            (date, total_flights, total_positions, avg_altitude_m, min_distance_km, updated_at)
            SELECT 
                DATE(?) as date,
                COUNT(DISTINCT f.id) as total_flights,
                COUNT(p.id) as total_positions,
                AVG(p.altitude_m) as avg_altitude_m,
                MIN(p.distance_from_home_km) as min_distance_km,
                CURRENT_TIMESTAMP as updated_at
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
            WHERE DATE(p.timestamp) = DATE(?)
        ''', (date, date))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Dictionary with statistical data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        conn.close()
        
        return {
            'total_flights': row[0] or 0,
            'unique_aircraft': row[1] or 0,
            'total_positions': row[2] or 0,
            'avg_altitude_m': row[3] or 0,
            'closest_approach_km': row[4],
            'first_observation': row[5],
            'last_observation': row[6]
        }
    
    def get_flight_by_id(self, flight_id: int) -> Optional[Dict[str, Any]]:
        """
        Get flight details by ID.
        
        Args:
            flight_id: Flight ID
        
        Returns:
            Flight data dictionary or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM flights WHERE id = ?', (flight_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_positions_for_flight(self, flight_id: int) -> List[Dict[str, Any]]:
        """
        Get all positions for a flight.
        
        Args:
            flight_id: Flight ID
        
        Returns:
            List of position dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM positions 
            WHERE flight_id = ? 
            ORDER BY timestamp
        ''', (flight_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def close(self):
        """Close database connection."""
        pass  # Using context managers, no persistent connection
