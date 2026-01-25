"""
LARA Flight Collector
Collects flight data from OpenSky Network API and stores in database.
"""

import requests
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from .database import FlightDatabase
from .config import Config
from .utils import haversine_distance, get_bounding_box, parse_state_vector
from .constants import MIN_UPDATE_INTERVAL


class FlightCollector:
    """Collects and stores flight data from OpenSky Network."""
    
    def __init__(self, config: Config):
        """
        Initialize flight collector.
        
        Args:
            config: LARA configuration object
        """
        self.config = config
        self.db = FlightDatabase(config.db_path)
        self.home_lat = config.home_latitude
        self.home_lon = config.home_longitude
        self.radius_km = config.radius_km
        self.update_interval = max(config.update_interval, MIN_UPDATE_INTERVAL)
        self.api_url = config.api_url
        self.api_timeout = config.api_timeout
        
        self.iteration_count = 0
        self.last_date = None
    
    def fetch_flights(self) -> List[list]:
        """
        Fetch flights from OpenSky Network API.
        
        Returns:
            List of state vectors from API
        """
        # Get bounding box for API query
        lamin, lomin, lamax, lomax = get_bounding_box(
            self.home_lat, self.home_lon, self.radius_km
        )
        
        url = f"{self.api_url}?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
        
        try:
            response = requests.get(url, timeout=self.api_timeout)
            response.raise_for_status()
            data = response.json()
            
            if data and 'states' in data and data['states']:
                return data['states']
            else:
                return []
        
        except requests.exceptions.Timeout:
            print(f"⚠️  API request timeout after {self.api_timeout}s")
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching data: {e}")
            return []
        except ValueError as e:
            print(f"❌ Error parsing API response: {e}")
            return []
    
    def process_flight(self, state: list, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Process a single flight state vector.
        
        Args:
            state: State vector from OpenSky API
            timestamp: Current timestamp
        
        Returns:
            Dictionary with flight info or None if invalid
        """
        try:
            # Parse state vector
            state_data = parse_state_vector(state)
            
            lat = state_data.get('latitude')
            lon = state_data.get('longitude')
            
            # Skip if no position data
            if lat is None or lon is None:
                return None
            
            # Calculate distance from home
            distance = haversine_distance(self.home_lat, self.home_lon, lat, lon)
            
            # Skip if outside radius
            if distance > self.radius_km:
                return None
            
            # Get or create flight record
            icao24 = state_data['icao24']
            callsign = state_data['callsign'] or 'UNKNOWN'
            origin_country = state_data['origin_country']
            
            flight_id = self.db.get_or_create_flight(
                icao24, callsign, origin_country, timestamp
            )
            
            # Store position update
            self.db.add_position(flight_id, state_data, distance, timestamp)
            
            return {
                'flight_id': flight_id,
                'callsign': callsign,
                'distance': distance,
                'altitude': state_data.get('baro_altitude') or state_data.get('geo_altitude'),
                'velocity': state_data.get('velocity')
            }
        
        except Exception as e:
            print(f"⚠️  Error processing flight: {e}")
            return None
    
    def display_flight_info(self, flight_info: Dict[str, Any]):
        """
        Display flight information to console.
        
        Args:
            flight_info: Dictionary with flight data
        """
        callsign = flight_info['callsign']
        distance = flight_info['distance']
        altitude = flight_info['altitude']
        velocity = flight_info['velocity']
        
        print(f"  ✈️  {callsign:8s} | {distance:5.1f} km | ", end="")
        
        if altitude:
            print(f"{altitude:6.0f} m | ", end="")
        
        if velocity:
            from .constants import MS_TO_KMH
            print(f"{velocity * MS_TO_KMH:5.1f} km/h", end="")
        
        print()
    
    def print_header(self):
        """Print collector header information."""
        print("=" * 70)
        print("🛩️  LARA - Local Air Route Analysis")
        print("📍 Data Collection Module")
        print("=" * 70)
        print(f"Location:  {self.home_lat}°N, {self.home_lon}°E")
        print(f"Name:      {self.config.location_name}")
        print(f"Radius:    {self.radius_km} km")
        print(f"Interval:  {self.update_interval}s")
        print(f"Database:  {self.config.db_path}")
        print("=" * 70)
    
    def print_statistics(self):
        """Print current database statistics."""
        stats = self.db.get_statistics()
        print(f"\n📊 Current Database Statistics:")
        print(f"   Total flights tracked: {stats['total_flights']:,}")
        print(f"   Unique aircraft: {stats['unique_aircraft']:,}")
        print(f"   Total positions logged: {stats['total_positions']:,}")
        if stats['first_observation']:
            print(f"   Data collection started: {stats['first_observation']}")
    
    def run_single_iteration(self) -> int:
        """
        Run a single data collection iteration.
        
        Returns:
            Number of flights detected
        """
        self.iteration_count += 1
        timestamp = datetime.now().isoformat()
        current_date = datetime.now().date()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan #{self.iteration_count}...", end=" ")
        
        # Fetch flights from API
        flights = self.fetch_flights()
        
        if not flights:
            print("No flights detected")
            return 0
        
        # Process each flight
        detected_flights = []
        for state in flights:
            flight_info = self.process_flight(state, timestamp)
            if flight_info:
                detected_flights.append(flight_info)
        
        # Sort by distance (closest first)
        detected_flights.sort(key=lambda x: x['distance'])
        
        print(f"Found {len(detected_flights)} flight(s)")
        
        # Display flight information
        for flight_info in detected_flights:
            self.display_flight_info(flight_info)
        
        # Update daily stats if date changed
        if self.last_date != current_date:
            if self.last_date:
                self.db.update_daily_stats(self.last_date.isoformat())
            self.last_date = current_date
        
        return len(detected_flights)
    
    def run(self):
        """
        Run continuous data collection.
        
        Runs until interrupted by Ctrl+C.
        """
        self.print_header()
        self.print_statistics()
        
        print("\n🔄 Starting data collection... (Press Ctrl+C to stop)\n")
        
        try:
            while True:
                self.run_single_iteration()
                
                # Show updated stats every 10 iterations
                if self.iteration_count % 10 == 0:
                    stats = self.db.get_statistics()
                    print(f"\n📈 Stats: {stats['total_flights']:,} flights, "
                          f"{stats['total_positions']:,} positions logged\n")
                
                time.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            self._handle_shutdown()
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self._handle_shutdown()
    
    def _handle_shutdown(self):
        """Handle graceful shutdown."""
        print("\n\n👋 Stopping data collection...")
        
        # Update final daily stats
        if self.last_date:
            self.db.update_daily_stats(self.last_date.isoformat())
        
        # Print final statistics
        stats = self.db.get_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Total flights tracked: {stats['total_flights']:,}")
        print(f"   Unique aircraft: {stats['unique_aircraft']:,}")
        print(f"   Total positions logged: {stats['total_positions']:,}")
        
        if stats['avg_altitude_m']:
            print(f"   Average altitude: {stats['avg_altitude_m']:.0f} m")
        
        if stats['closest_approach_km']:
            print(f"   Closest approach: {stats['closest_approach_km']:.2f} km")
        
        print(f"\n💾 Data saved to: {self.config.db_path}")
