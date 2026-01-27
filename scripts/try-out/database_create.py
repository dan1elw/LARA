import requests
import time
import sqlite3
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import json
import os

# Your home coordinates (Frankfurt a.M., Germany)
HOME_LAT = 50.1137
HOME_LON = 8.6796
RADIUS_KM = 50  # Search radius in kilometers
DB_PATH = "scripts/try/lara_flights.db"


class FlightDatabase:
    """Manages SQLite database for flight data storage"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table for unique flights (one entry per flight session)
        cursor.execute("""
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
                position_count INTEGER DEFAULT 0
            )
        """)

        # Table for position updates (tracking route over time)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id INTEGER,
                timestamp TIMESTAMP,
                latitude REAL,
                longitude REAL,
                altitude_m REAL,
                geo_altitude_m REAL,
                velocity_ms REAL,
                heading REAL,
                vertical_rate_ms REAL,
                distance_from_home_km REAL,
                on_ground BOOLEAN,
                FOREIGN KEY (flight_id) REFERENCES flights(id)
            )
        """)

        # Table for daily statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_flights INTEGER,
                total_positions INTEGER,
                avg_altitude_m REAL,
                min_distance_km REAL
            )
        """)

        # Create indexes for better query performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_flights_icao24 ON flights(icao24)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_flight_id ON positions(flight_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_timestamp ON positions(timestamp)"
        )

        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {self.db_path}")

    def get_or_create_flight(self, icao24, callsign, origin_country, timestamp):
        """Get existing flight or create new one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Look for active flight (seen within last 30 minutes)
        cursor.execute(
            """
            SELECT id FROM flights 
            WHERE icao24 = ? AND callsign = ?
            AND datetime(last_seen) > datetime(?, '-30 minutes')
            ORDER BY last_seen DESC LIMIT 1
        """,
            (icao24, callsign, timestamp),
        )

        result = cursor.fetchone()

        if result:
            flight_id = result[0]
            # Update last_seen
            cursor.execute(
                "UPDATE flights SET last_seen = ? WHERE id = ?", (timestamp, flight_id)
            )
        else:
            # Create new flight entry
            cursor.execute(
                """
                INSERT INTO flights (icao24, callsign, origin_country, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """,
                (icao24, callsign, origin_country, timestamp, timestamp),
            )
            flight_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return flight_id

    def add_position(self, flight_id, state, distance_km, timestamp):
        """Add position update for a flight"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert position
        cursor.execute(
            """
            INSERT INTO positions (
                flight_id, timestamp, latitude, longitude, altitude_m, geo_altitude_m,
                velocity_ms, heading, vertical_rate_ms, distance_from_home_km, on_ground
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                flight_id,
                timestamp,
                state[6],  # latitude
                state[5],  # longitude
                state[7],  # baro_altitude
                state[13],  # geo_altitude
                state[9],  # velocity
                state[10],  # true_track
                state[11],  # vertical_rate
                distance_km,
                state[8],  # on_ground
            ),
        )

        # Update flight statistics
        cursor.execute(
            """
            UPDATE flights SET
                position_count = position_count + 1,
                min_distance_km = COALESCE(MIN(min_distance_km, ?), ?),
                max_altitude_m = COALESCE(MAX(max_altitude_m, ?), ?),
                min_altitude_m = COALESCE(MIN(min_altitude_m, ?), ?)
            WHERE id = ?
        """,
            (
                distance_km,
                distance_km,
                state[7] or state[13],
                state[7] or state[13],
                state[7] or state[13],
                state[7] or state[13],
                flight_id,
            ),
        )

        conn.commit()
        conn.close()

    def update_daily_stats(self, date):
        """Update daily statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO daily_stats (date, total_flights, total_positions, avg_altitude_m, min_distance_km)
            SELECT 
                DATE(?) as date,
                COUNT(DISTINCT f.id) as total_flights,
                COUNT(p.id) as total_positions,
                AVG(p.altitude_m) as avg_altitude_m,
                MIN(p.distance_from_home_km) as min_distance_km
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
            WHERE DATE(p.timestamp) = DATE(?)
        """,
            (date, date),
        )

        conn.commit()
        conn.close()

    def get_statistics(self):
        """Get overall statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(DISTINCT f.id) as total_flights,
                COUNT(p.id) as total_positions,
                AVG(p.altitude_m) as avg_altitude,
                MIN(p.distance_from_home_km) as closest_approach,
                MIN(f.first_seen) as first_observation,
                MAX(f.last_seen) as last_observation
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
        """)

        stats = cursor.fetchone()
        conn.close()

        return {
            "total_flights": stats[0] or 0,
            "total_positions": stats[1] or 0,
            "avg_altitude_m": stats[2] or 0,
            "closest_approach_km": stats[3] or 0,
            "first_observation": stats[4],
            "last_observation": stats[5],
        }


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    R = 6371  # Radius of earth in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def get_bounding_box(lat, lon, radius_km):
    """Calculate bounding box for API query"""
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * cos(radians(lat)))
    return (lat - lat_delta, lon - lon_delta, lat + lat_delta, lon + lon_delta)


def fetch_flights():
    """Fetch flights from OpenSky Network API"""
    lamin, lomin, lamax, lomax = get_bounding_box(HOME_LAT, HOME_LON, RADIUS_KM)
    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["states"] if data and "states" in data else []
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return []


def display_flight_info(state, distance):
    """Display flight information"""
    callsign = state[1].strip() if state[1] else "N/A"
    altitude = state[7] if state[7] else state[13]
    velocity = state[9]

    print(f"  ✈️  {callsign:8s} | {distance:5.1f} km | ", end="")
    if altitude:
        print(f"{altitude:6.0f} m | ", end="")
    if velocity:
        print(f"{velocity * 3.6:5.1f} km/h", end="")
    print()


def main():
    """Main data collection loop"""
    print("=" * 70)
    print("🛩️  LARA - Local Air Route Analysis")
    print("📍 Data Collection Module")
    print("=" * 70)
    print(f"Location:  {HOME_LAT}°N, {HOME_LON}°E (Neustadt an der Weinstraße)")
    print(f"Radius:    {RADIUS_KM} km")
    print(f"Database:  {DB_PATH}")
    print("=" * 70)

    # Initialize database
    db = FlightDatabase(DB_PATH)

    # Show initial statistics
    stats = db.get_statistics()
    print(f"\n📊 Current Database Statistics:")
    print(f"   Total flights tracked: {stats['total_flights']}")
    print(f"   Total positions logged: {stats['total_positions']}")
    if stats["first_observation"]:
        print(f"   Data collection started: {stats['first_observation']}")

    print("\n🔄 Starting data collection... (Press Ctrl+C to stop)\n")

    try:
        iteration = 0
        last_date = None

        while True:
            iteration += 1
            timestamp = datetime.now().isoformat()
            current_date = datetime.now().date()

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Scan #{iteration}...", end=" "
            )

            flights = fetch_flights()

            if flights:
                nearby_flights = []

                for state in flights:
                    lat, lon = state[6], state[5]
                    if lat and lon:
                        distance = haversine_distance(HOME_LAT, HOME_LON, lat, lon)
                        if distance <= RADIUS_KM:
                            nearby_flights.append((distance, state))

                nearby_flights.sort(key=lambda x: x[0])

                print(f"Found {len(nearby_flights)} flight(s)")

                for distance, state in nearby_flights:
                    icao24 = state[0]
                    callsign = state[1].strip() if state[1] else "UNKNOWN"
                    origin_country = state[2]

                    # Store in database
                    flight_id = db.get_or_create_flight(
                        icao24, callsign, origin_country, timestamp
                    )
                    db.add_position(flight_id, state, distance, timestamp)

                    # Display
                    display_flight_info(state, distance)

                # Update daily stats if date changed
                if last_date != current_date:
                    if last_date:
                        db.update_daily_stats(last_date)
                    last_date = current_date

            else:
                print("No flights detected")

            # Show updated stats every 10 iterations
            if iteration % 10 == 0:
                stats = db.get_statistics()
                print(
                    f"\n📈 Stats: {stats['total_flights']} flights, {stats['total_positions']} positions logged"
                )
                print()

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n👋 Stopping data collection...")
        db.update_daily_stats(datetime.now().date())
        stats = db.get_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Total flights tracked: {stats['total_flights']}")
        print(f"   Total positions logged: {stats['total_positions']}")
        print(f"   Average altitude: {stats['avg_altitude_m']:.0f} m")
        print(f"   Closest approach: {stats['closest_approach_km']:.2f} km")
        print(f"\n💾 Data saved to: {DB_PATH}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
