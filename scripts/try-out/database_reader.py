import sqlite3
import sys
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = "scripts/try/lara_flights.db"

class LARAReader:
    """Read and query LARA flight database"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"❌ Error connecting to database: {e}")
            sys.exit(1)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_overview(self):
        """Get overall database statistics"""
        cursor = self.conn.cursor()
        
        # Overall stats
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
        
        stats = cursor.fetchone()
        
        print("=" * 70)
        print("📊 LARA DATABASE OVERVIEW")
        print("=" * 70)
        print(f"Total Flights Tracked:    {stats['total_flights']:,}")
        print(f"Unique Aircraft:          {stats['unique_aircraft']:,}")
        print(f"Total Position Updates:   {stats['total_positions']:,}")
        print(f"Average Altitude:         {stats['avg_altitude']:.0f} m ({stats['avg_altitude'] * 3.28084:.0f} ft)")
        print(f"Closest Approach:         {stats['closest_approach']:.2f} km")
        print(f"First Observation:        {stats['first_observation']}")
        print(f"Last Observation:         {stats['last_observation']}")
        print("=" * 70)
    
    def get_recent_flights(self, hours=24, limit=20):
        """Get recent flights"""
        cursor = self.conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT 
                f.callsign,
                f.icao24,
                f.origin_country,
                f.first_seen,
                f.last_seen,
                f.min_distance_km,
                f.max_altitude_m,
                f.min_altitude_m,
                f.position_count,
                CAST((julianday(f.last_seen) - julianday(f.first_seen)) * 24 * 60 AS INTEGER) as duration_minutes
            FROM flights f
            WHERE f.first_seen >= ?
            ORDER BY f.first_seen DESC
            LIMIT ?
        ''', (cutoff, limit))
        
        flights = cursor.fetchall()
        
        print(f"\n✈️  RECENT FLIGHTS (Last {hours} hours)")
        print("=" * 110)
        print(f"{'Callsign':<10} {'ICAO24':<8} {'Country':<20} {'First Seen':<20} {'Duration':<10} {'Min Dist':<10} {'Altitude Range':<15}")
        print("-" * 110)
        
        for flight in flights:
            callsign = flight['callsign'] or 'N/A'
            duration = f"{flight['duration_minutes']}m" if flight['duration_minutes'] else 'N/A'
            alt_range = f"{flight['min_altitude_m']:.0f}-{flight['max_altitude_m']:.0f}m" if flight['max_altitude_m'] else 'N/A'
            
            print(f"{callsign:<10} {flight['icao24']:<8} {flight['origin_country']:<20} "
                  f"{flight['first_seen']:<20} {duration:<10} {flight['min_distance_km']:>8.2f} km {alt_range:<15}")
        
        print(f"\nTotal: {len(flights)} flights")
    
    def get_top_airlines(self, limit=10):
        """Get most common airlines/callsigns"""
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
        
        airlines = cursor.fetchall()
        
        print(f"\n🏢 TOP {limit} AIRLINES/OPERATORS")
        print("=" * 70)
        print(f"{'Code':<6} {'Flights':<10} {'Avg Min Distance':<20} {'Avg Altitude':<15}")
        print("-" * 70)
        
        for airline in airlines:
            print(f"{airline['airline_code']:<6} {airline['flight_count']:<10} "
                  f"{airline['avg_min_distance']:>16.2f} km {airline['avg_max_altitude']:>12.0f} m")
    
    def get_countries(self):
        """Get flights by country"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                origin_country,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_min_distance
            FROM flights
            GROUP BY origin_country
            ORDER BY flight_count DESC
            LIMIT 15
        ''')
        
        countries = cursor.fetchall()
        
        print(f"\n🌍 FLIGHTS BY COUNTRY")
        print("=" * 60)
        print(f"{'Country':<25} {'Flights':<12} {'Avg Min Distance':<15}")
        print("-" * 60)
        
        for country in countries:
            print(f"{country['origin_country']:<25} {country['flight_count']:<12} {country['avg_min_distance']:>12.2f} km")
    
    def get_hourly_distribution(self):
        """Get flight distribution by hour of day"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                CAST(strftime('%H', first_seen) AS INTEGER) as hour,
                COUNT(*) as flight_count
            FROM flights
            GROUP BY hour
            ORDER BY hour
        ''')
        
        hours = cursor.fetchall()
        
        print(f"\n🕐 HOURLY FLIGHT DISTRIBUTION")
        print("=" * 70)
        
        if hours:
            max_count = max(h['flight_count'] for h in hours)
            
            for hour_data in hours:
                hour = hour_data['hour']
                count = hour_data['flight_count']
                bar_length = int((count / max_count) * 40)
                bar = '█' * bar_length
                print(f"{hour:02d}:00 | {bar:<40} {count:>4} flights")
    
    def get_altitude_distribution(self):
        """Get altitude distribution"""
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
            ORDER BY altitude_m
        ''')
        
        altitudes = cursor.fetchall()
        
        print(f"\n📏 ALTITUDE DISTRIBUTION")
        print("=" * 70)
        
        if altitudes:
            max_count = max(a['count'] for a in altitudes)
            
            for alt_data in altitudes:
                range_name = alt_data['altitude_range']
                count = alt_data['count']
                bar_length = int((count / max_count) * 40)
                bar = '█' * bar_length
                print(f"{range_name:<15} | {bar:<40} {count:>6} positions")
    
    def get_closest_flights(self, limit=10):
        """Get flights that came closest to home"""
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
        
        flights = cursor.fetchall()
        
        print(f"\n🎯 CLOSEST FLIGHTS")
        print("=" * 90)
        print(f"{'Callsign':<10} {'ICAO24':<8} {'Country':<20} {'Distance':<12} {'Altitude':<12} {'Position':<20}")
        print("-" * 90)
        
        for flight in flights:
            callsign = flight['callsign'] or 'N/A'
            altitude = f"{flight['min_altitude_m']:.0f}m" if flight['min_altitude_m'] else 'N/A'
            position = f"{flight['latitude']:.4f},{flight['longitude']:.4f}" if flight['latitude'] else 'N/A'
            
            print(f"{callsign:<10} {flight['icao24']:<8} {flight['origin_country']:<20} "
                  f"{flight['min_distance_km']:>9.2f} km {altitude:<12} {position:<20}")
    
    def get_daily_stats(self, days=7):
        """Get daily statistics"""
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
        
        stats = cursor.fetchall()
        
        print(f"\n📅 DAILY STATISTICS (Last {days} days)")
        print("=" * 70)
        print(f"{'Date':<12} {'Flights':<10} {'Avg Min Distance':<20} {'Avg Altitude':<15}")
        print("-" * 70)
        
        for stat in stats:
            print(f"{stat['date']:<12} {stat['flight_count']:<10} "
                  f"{stat['avg_min_distance']:>16.2f} km {stat['avg_altitude']:>12.0f} m")
    
    def search_flight(self, callsign):
        """Search for specific flight by callsign"""
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
        
        flights = cursor.fetchall()
        
        if not flights:
            print(f"\n❌ No flights found matching '{callsign}'")
            return
        
        print(f"\n🔍 SEARCH RESULTS FOR '{callsign}'")
        print("=" * 70)
        
        for flight in flights:
            print(f"\nFlight ID: {flight['id']}")
            print(f"Callsign: {flight['callsign']}")
            print(f"ICAO24: {flight['icao24']}")
            print(f"Country: {flight['origin_country']}")
            print(f"First Seen: {flight['first_seen']}")
            print(f"Last Seen: {flight['last_seen']}")
            print(f"Positions Tracked: {flight['position_count']}")
            print(f"Min Distance: {flight['min_distance_km']:.2f} km")
            print(f"Altitude Range: {flight['min_altitude_m']:.0f}m - {flight['max_altitude_m']:.0f}m")
            print("-" * 70)
    
    def get_flight_route(self, flight_id):
        """Get complete route for a specific flight"""
        cursor = self.conn.cursor()
        
        # Get flight info
        cursor.execute('SELECT * FROM flights WHERE id = ?', (flight_id,))
        flight = cursor.fetchone()
        
        if not flight:
            print(f"❌ Flight ID {flight_id} not found")
            return
        
        # Get positions
        cursor.execute('''
            SELECT * FROM positions 
            WHERE flight_id = ? 
            ORDER BY timestamp
        ''', (flight_id,))
        
        positions = cursor.fetchall()
        
        print(f"\n🗺️  FLIGHT ROUTE - {flight['callsign']} ({flight['icao24']})")
        print("=" * 100)
        print(f"Country: {flight['origin_country']}")
        print(f"Duration: {flight['first_seen']} to {flight['last_seen']}")
        print(f"Positions: {len(positions)}")
        print("=" * 100)
        print(f"{'Time':<20} {'Lat':<12} {'Lon':<12} {'Altitude':<12} {'Speed':<12} {'Distance':<10}")
        print("-" * 100)
        
        for pos in positions:
            altitude = f"{pos['altitude_m']:.0f}m" if pos['altitude_m'] else 'N/A'
            speed = f"{pos['velocity_ms'] * 3.6:.0f} km/h" if pos['velocity_ms'] else 'N/A'
            
            print(f"{pos['timestamp']:<20} {pos['latitude']:<12.4f} {pos['longitude']:<12.4f} "
                  f"{altitude:<12} {speed:<12} {pos['distance_from_home_km']:>8.2f} km")

def print_menu():
    """Print interactive menu"""
    print("\n" + "=" * 70)
    print("🛩️  LARA DATABASE READER - MAIN MENU")
    print("=" * 70)
    print("1.  Overview & Statistics")
    print("2.  Recent Flights (24h)")
    print("3.  Top Airlines/Operators")
    print("4.  Flights by Country")
    print("5.  Hourly Distribution")
    print("6.  Altitude Distribution")
    print("7.  Closest Flights")
    print("8.  Daily Statistics")
    print("9.  Search Flight by Callsign")
    print("10. View Flight Route (by ID)")
    print("0.  Exit")
    print("=" * 70)

def main():
    """Main interactive menu"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH
    
    reader = LARAReader(db_path)
    
    try:
        while True:
            print_menu()
            choice = input("\nEnter your choice (0-10): ").strip()
            
            if choice == '0':
                print("\n👋 Goodbye!")
                break
            elif choice == '1':
                reader.get_overview()
            elif choice == '2':
                reader.get_recent_flights()
            elif choice == '3':
                reader.get_top_airlines()
            elif choice == '4':
                reader.get_countries()
            elif choice == '5':
                reader.get_hourly_distribution()
            elif choice == '6':
                reader.get_altitude_distribution()
            elif choice == '7':
                reader.get_closest_flights()
            elif choice == '8':
                reader.get_daily_stats()
            elif choice == '9':
                callsign = input("Enter callsign to search: ").strip()
                reader.search_flight(callsign)
            elif choice == '10':
                try:
                    flight_id = int(input("Enter flight ID: ").strip())
                    reader.get_flight_route(flight_id)
                except ValueError:
                    print("❌ Invalid flight ID")
            else:
                print("❌ Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    finally:
        reader.close()

if __name__ == "__main__":
    main()