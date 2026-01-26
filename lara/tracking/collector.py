"""
LARA Flight Collector with OAuth2 Authentication
"""

import requests
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from .database import FlightDatabase
from .config import Config
from .utils import haversine_distance, get_bounding_box, parse_state_vector
from .constants import MIN_UPDATE_INTERVAL
from .auth import create_auth_from_config, OpenSkyAuth


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
        
        # Initialize OAuth2 authentication
        self.auth = create_auth_from_config(config)
        
        self.iteration_count = 0
        self.last_date = None
        self.consecutive_empty_scans = 0
        self.total_empty_scans = 0
        self.rate_limit_count = 0
        self.last_request_time = 0
    
    def fetch_flights(self) -> List[list]:
        """
        Fetch flights from OpenSky Network API.
        
        Returns:
            List of state vectors from API, or empty list if no data
        """
        # Get bounding box for API query
        try:
            lamin, lomin, lamax, lomax = get_bounding_box(
                self.home_lat, self.home_lon, self.radius_km
            )
        except Exception as e:
            print(f"⚠️  Error calculating bounding box: {e}")
            return []
        
        params = {
            'lamin': lamin,
            'lomin': lomin,
            'lamax': lamax,
            'lomax': lomax
        }
        
        # Enforce minimum time between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.update_interval:
            time.sleep(self.update_interval - time_since_last)
        
        try:
            # Use OAuth2 if available, otherwise anonymous
            if self.auth:
                response = self.auth.make_authenticated_request(
                    self.api_url,
                    params=params,
                    timeout=self.api_timeout
                )
            else:
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=self.api_timeout
                )
            
            self.last_request_time = time.time()
            
            # Handle rate limiting (429 error)
            if response.status_code == 429:
                self.rate_limit_count += 1
                
                retry_after = response.headers.get('Retry-After')
                
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except:
                        wait_time = 60
                else:
                    wait_time = min(60 * self.rate_limit_count, 300)
                
                print(f"⚠️  Rate limited by OpenSky Network (429)")
                print(f"   This is hit #{self.rate_limit_count}")
                print(f"   Waiting {wait_time} seconds before retrying...")
                
                if not self.auth:
                    print(f"   💡 Tip: Set up OAuth2 authentication for better limits")
                    print(f"   💡 Download credentials.json from opensky-network.org")
                
                time.sleep(wait_time)
                
                # Try again after waiting
                try:
                    if self.auth:
                        response = self.auth.make_authenticated_request(
                            self.api_url,
                            params=params,
                            timeout=self.api_timeout
                        )
                    else:
                        response = requests.get(
                            self.api_url,
                            params=params,
                            timeout=self.api_timeout
                        )
                    
                    self.last_request_time = time.time()
                    
                    if response.status_code == 429:
                        print(f"   Still rate limited after waiting. Skipping this scan.")
                        return []
                except Exception as e:
                    print(f"   Retry failed: {e}")
                    return []
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Reset rate limit counter on success
            self.rate_limit_count = 0
            
            data = response.json()
            
            # Handle different response structures
            if not data:
                return []
            
            if 'states' not in data:
                return []
            
            states = data['states']
            if states is None:
                return []
            
            if not isinstance(states, list):
                return []
            
            return states
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"❌ Authentication failed (401): Your OAuth2 credentials may be invalid, check your credentials.json file")
                return []
            elif e.response.status_code == 429:
                # Already handled above
                return []
            else:
                print(f"❌ HTTP Error {e.response.status_code}: {e}")
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
        
        except Exception as e:
            print(f"❌ Unexpected error fetching flights: {e}")
            return []
    
    def process_flight(self, state: list, timestamp: str) -> Optional[Dict[str, Any]]:
        """Process a single flight state vector."""
        try:
            if not state or not isinstance(state, list):
                return None
            
            state_data = parse_state_vector(state)
            
            lat = state_data.get('latitude')
            lon = state_data.get('longitude')
            
            if lat is None or lon is None:
                return None
            
            distance = haversine_distance(self.home_lat, self.home_lon, lat, lon)
            
            if distance > self.radius_km:
                return None
            
            icao24 = state_data.get('icao24')
            if not icao24:
                return None
            
            callsign = state_data.get('callsign') or 'UNKNOWN'
            origin_country = state_data.get('origin_country') or 'Unknown'
            
            flight_id = self.db.get_or_create_flight(
                icao24, callsign, origin_country, timestamp
            )
            
            self.db.add_position(flight_id, state_data, distance, timestamp)
            
            return {
                'flight_id': flight_id,
                'callsign': callsign,
                'distance': distance,
                'altitude': state_data.get('baro_altitude') or state_data.get('geo_altitude'),
                'velocity': state_data.get('velocity')
            }
        
        except Exception as e:
            return None
    
    def display_flight_info(self, flight_info: Dict[str, Any]):
        """Display flight information to console."""
        callsign = flight_info.get('callsign', 'UNKNOWN')
        distance = flight_info.get('distance', 0)
        altitude = flight_info.get('altitude')
        velocity = flight_info.get('velocity')
        
        print(f"  ✈️  {callsign:8s} | {distance:5.1f} km | ", end="")
        
        if altitude is not None:
            print(f"{altitude:6.0f} m | ", end="")
        else:
            print(f"{'N/A':>6s} m | ", end="")
        
        if velocity is not None:
            from .constants import MS_TO_KMH
            print(f"{velocity * MS_TO_KMH:5.1f} km/h", end="")
        else:
            print(f"{'N/A':>5s} km/h", end="")
        
        print()
    
    def print_header(self):
        """Print collector header information."""
        print("\n" + "=" * 70)
        print("🛩️  LARA - Local Air Route Analysis")
        print("=" * 70)
        print(f"Location:   {self.home_lat}°N, {self.home_lon}°E, {self.config.location_name}")
        print(f"Radius:     {self.radius_km}km")
        print(f"Interval:   {self.update_interval}s")
        print(f"Database:   {self.config.db_path}")
        
        # Show authentication status
        if self.auth:
            print(f"Auth:       OAuth2 (Client: {self.auth.client_id})")
        else:
            print(f"Auth:       Anonymous (for higher limits, set up OAuth2 credentials)")
        
        print("=" * 70)
        
        # Warning for anonymous users with low interval
        if self.update_interval < 15 and not self.auth:
            print("\n⚠️  WARNING: Update interval <15s without authentication")
            print("   You may encounter rate limiting (HTTP 429 errors)")
            print("   Set up OAuth2: Download credentials.json from opensky-network.org")
            print("=" * 70)
    
    def print_statistics(self):
        """Print current database statistics."""
        try:
            stats = self.db.get_statistics()
            print(f"\n📊 Current Database Statistics:")
            print(f"   Total flights tracked: {stats['total_flights']:,}")
            print(f"   Unique aircraft: {stats['unique_aircraft']:,}")
            print(f"   Total positions logged: {stats['total_positions']:,}")
            if stats.get('first_observation'):
                print(f"   Data collection started: {stats['first_observation']}")
        except Exception as e:
            print(f"⚠️  Could not retrieve statistics: {e}")
    
    def run_single_iteration(self) -> int:
        """Run a single data collection iteration."""
        self.iteration_count += 1
        timestamp = datetime.now().isoformat()
        current_date = datetime.now().date()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan #{self.iteration_count}...", end=" ")
        
        flights = self.fetch_flights()
        
        if not flights:
            self.consecutive_empty_scans += 1
            self.total_empty_scans += 1
            
            if self.consecutive_empty_scans == 1:
                print("No flights detected")
            elif self.consecutive_empty_scans >= 2:
                print(f"No flights detected ({self.consecutive_empty_scans} consecutive)")
            
            return 0
        
        detected_flights = []
        for state in flights:
            flight_info = self.process_flight(state, timestamp)
            if flight_info:
                detected_flights.append(flight_info)
        
        if not detected_flights:
            self.consecutive_empty_scans += 1
            self.total_empty_scans += 1
            print("No flights within tracking radius")
            return 0
        
        detected_flights.sort(key=lambda x: x['distance'])
        
        print(f"Found {len(detected_flights)} flight(s)")
        
        for flight_info in detected_flights:
            self.display_flight_info(flight_info)
        
        if self.last_date != current_date:
            if self.last_date:
                try:
                    self.db.update_daily_stats(self.last_date.isoformat())
                except Exception as e:
                    print(f"⚠️  Error updating daily stats: {e}")
            self.last_date = current_date
        
        return len(detected_flights)
    
    def run(self):
        """Run continuous data collection."""
        self.print_header()
        self.print_statistics()
        
        print("\n🔄 Starting data collection... (Press Ctrl+C to stop)\n")
        
        try:
            while True:
                try:
                    self.run_single_iteration()
                except Exception as e:
                    print(f"\n⚠️  Error in iteration {self.iteration_count}: {e}")
                    print("   Continuing with next scan...")
                
                if self.iteration_count % 10 == 0:
                    try:
                        stats = self.db.get_statistics()
                        empty_rate = (self.total_empty_scans / self.iteration_count) * 100
                        
                        print(f"\n📈 Stats after {self.iteration_count} scans:")
                        
                        auth_mode = "OAuth2" if self.auth else "Anonymous"
                        print(f"   Mode: {auth_mode}")
                        
                        print(f"   Flights: {stats['total_flights']:,} | "
                              f"Positions: {stats['total_positions']:,} | "
                              f"Empty scans: {empty_rate:.1f}%")
                        
                        if self.rate_limit_count > 0:
                            print(f"   ⚠️  Rate limit hits: {self.rate_limit_count}")
                        
                        print()
                    except Exception as e:
                        print(f"⚠️  Could not display stats: {e}")
                
                time.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            self._handle_shutdown()
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self._handle_shutdown()
    
    def _handle_shutdown(self):
        """Handle graceful shutdown."""
        print("\n\n👋 Stopping data collection...")
        
        if self.last_date:
            try:
                self.db.update_daily_stats(self.last_date.isoformat())
            except Exception as e:
                print(f"⚠️  Error updating final stats: {e}")
        
        try:
            stats = self.db.get_statistics()
            print(f"\n📊 Final Statistics:")
            print(f"   Total scans: {self.iteration_count:,}")
            print(f"   Empty scans: {self.total_empty_scans:,} ({(self.total_empty_scans/max(self.iteration_count, 1)*100):.1f}%)")
            
            if self.rate_limit_count > 0:
                print(f"   Rate limit hits: {self.rate_limit_count}")
                if not self.auth:
                    print(f"   💡 Set up OAuth2 for better limits")
            
            print(f"   Total flights tracked: {stats['total_flights']:,}")
            print(f"   Unique aircraft: {stats['unique_aircraft']:,}")
            print(f"   Total positions logged: {stats['total_positions']:,}")
            
            if stats.get('avg_altitude_m'):
                print(f"   Average altitude: {stats['avg_altitude_m']:.0f} m")
            
            if stats.get('closest_approach_km'):
                print(f"   Closest approach: {stats['closest_approach_km']:.2f} km")
            
            print(f"\n💾 Data saved to: {self.config.db_path}")
        except Exception as e:
            print(f"⚠️  Error displaying final statistics: {e}")
            print(f"💾 Data saved to: {self.config.db_path}")
