#!/usr/bin/env python3
"""
LARA Flight Data Reader Script

Usage:
    python scripts/read.py [--db DATABASE_FILE]
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking import FlightReader, Config
from lara.config import Constants


def print_menu():
    """Print interactive menu."""
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


def display_overview(reader: FlightReader):
    """Display overview statistics."""
    stats = reader.get_overview()

    print("=" * 70)
    print("📊 LARA DATABASE OVERVIEW")
    print("=" * 70)
    print(f"Total Flights Tracked:    {stats['total_flights']:,}")
    print(f"Unique Aircraft:          {stats['unique_aircraft']:,}")
    print(f"Total Position Updates:   {stats['total_positions']:,}")

    if stats["avg_altitude_m"]:
        avg_alt_ft = stats["avg_altitude_m"] * Constants.METERS_TO_FEET
        print(
            f"Average Altitude:         {stats['avg_altitude_m']:.0f} m ({avg_alt_ft:.0f} ft)"
        )

    if stats["closest_approach_km"]:
        print(f"Closest Approach:         {stats['closest_approach_km']:.2f} km")

    if stats["first_observation"]:
        print(f"First Observation:        {stats['first_observation']}")
    if stats["last_observation"]:
        print(f"Last Observation:         {stats['last_observation']}")

    print("=" * 70)


def display_recent_flights(reader: FlightReader):
    """Display recent flights."""
    flights = reader.get_recent_flights(hours=24, limit=20)

    print("\n✈️  RECENT FLIGHTS (Last 24 hours)")
    print("=" * 110)
    print(
        f"{'Callsign':<10} {'ICAO24':<8} {'Country':<20} {'First Seen':<20} {'Duration':<10} {'Min Dist':<10} {'Altitude Range':<15}"
    )
    print("-" * 110)

    for flight in flights:
        callsign = flight["callsign"] or "N/A"
        duration = (
            f"{flight['duration_minutes']}m" if flight["duration_minutes"] else "N/A"
        )

        if flight["max_altitude_m"] and flight["min_altitude_m"]:
            alt_range = (
                f"{flight['min_altitude_m']:.0f}-{flight['max_altitude_m']:.0f}m"
            )
        else:
            alt_range = "N/A"

        print(
            f"{callsign:<10} {flight['icao24']:<8} {flight['origin_country']:<20} "
            f"{flight['first_seen']:<20} {duration:<10} {flight['min_distance_km']:>8.2f} km {alt_range:<15}"
        )

    print(f"\nTotal: {len(flights)} flights")


def display_top_airlines(reader: FlightReader):
    """Display top airlines."""
    airlines = reader.get_top_airlines(limit=10)

    print("\n🏢 TOP 10 AIRLINES/OPERATORS")
    print("=" * 70)
    print(f"{'Code':<6} {'Flights':<10} {'Avg Min Distance':<20} {'Avg Altitude':<15}")
    print("-" * 70)

    for airline in airlines:
        print(
            f"{airline['airline_code']:<6} {airline['flight_count']:<10} "
            f"{airline['avg_min_distance']:>16.2f} km {airline['avg_max_altitude']:>12.0f} m"
        )


def display_countries(reader: FlightReader):
    """Display flights by country."""
    countries = reader.get_countries(limit=15)

    print("\n🌍 FLIGHTS BY COUNTRY")
    print("=" * 60)
    print(f"{'Country':<25} {'Flights':<12} {'Avg Min Distance':<15}")
    print("-" * 60)

    for country in countries:
        print(
            f"{country['origin_country']:<25} {country['flight_count']:<12} "
            f"{country['avg_min_distance']:>12.2f} km"
        )


def display_hourly_distribution(reader: FlightReader):
    """Display hourly distribution."""
    hours = reader.get_hourly_distribution()

    print("\n🕐 HOURLY FLIGHT DISTRIBUTION")
    print("=" * 70)

    if hours:
        max_count = max(h["flight_count"] for h in hours)

        for hour_data in hours:
            hour = hour_data["hour"]
            count = hour_data["flight_count"]
            bar_length = int((count / max_count) * 40)
            bar = "█" * bar_length
            print(f"{hour:02d}:00 | {bar:<40} {count:>4} flights")


def display_altitude_distribution(reader: FlightReader):
    """Display altitude distribution."""
    altitudes = reader.get_altitude_distribution()

    print("\n📏 ALTITUDE DISTRIBUTION")
    print("=" * 70)

    if altitudes:
        max_count = max(a["count"] for a in altitudes)

        for alt_data in altitudes:
            range_name = alt_data["altitude_range"]
            count = alt_data["count"]
            bar_length = int((count / max_count) * 40)
            bar = "█" * bar_length
            print(f"{range_name:<15} | {bar:<40} {count:>6} positions")


def display_closest_flights(reader: FlightReader):
    """Display closest flights."""
    flights = reader.get_closest_flights(limit=10)

    print("\n🎯 CLOSEST FLIGHTS")
    print("=" * 90)
    print(
        f"{'Callsign':<10} {'ICAO24':<8} {'Country':<20} {'Distance':<12} {'Altitude':<12} {'Position':<20}"
    )
    print("-" * 90)

    for flight in flights:
        callsign = flight["callsign"] or "N/A"
        altitude = (
            f"{flight['min_altitude_m']:.0f}m" if flight["min_altitude_m"] else "N/A"
        )
        position = (
            f"{flight['latitude']:.4f},{flight['longitude']:.4f}"
            if flight["latitude"]
            else "N/A"
        )

        print(
            f"{callsign:<10} {flight['icao24']:<8} {flight['origin_country']:<20} "
            f"{flight['min_distance_km']:>9.2f} km {altitude:<12} {position:<20}"
        )


def display_daily_stats(reader: FlightReader):
    """Display daily statistics."""
    stats = reader.get_daily_stats(days=7)

    print("\n📅 DAILY STATISTICS (Last 7 days)")
    print("=" * 70)
    print(f"{'Date':<12} {'Flights':<10} {'Avg Min Distance':<20} {'Avg Altitude':<15}")
    print("-" * 70)

    for stat in stats:
        print(
            f"{stat['date']:<12} {stat['flight_count']:<10} "
            f"{stat['avg_min_distance']:>16.2f} km {stat['avg_altitude']:>12.0f} m"
        )


def search_flight(reader: FlightReader, callsign: str):
    """Search for flights by callsign."""
    flights = reader.search_flight(callsign)

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

        if flight["min_distance_km"]:
            print(f"Min Distance: {flight['min_distance_km']:.2f} km")
        if flight["min_altitude_m"] and flight["max_altitude_m"]:
            print(
                f"Altitude Range: {flight['min_altitude_m']:.0f}m - {flight['max_altitude_m']:.0f}m"
            )

        print("-" * 70)


def display_flight_route(reader: FlightReader, flight_id: int):
    """Display flight route."""
    result = reader.get_flight_route(flight_id)

    if not result:
        print(f"❌ Flight ID {flight_id} not found")
        return

    flight, positions = result

    print(f"\n🗺️  FLIGHT ROUTE - {flight['callsign']} ({flight['icao24']})")
    print("=" * 100)
    print(f"Country: {flight['origin_country']}")
    print(f"Duration: {flight['first_seen']} to {flight['last_seen']}")
    print(f"Positions: {len(positions)}")
    print("=" * 100)
    print(
        f"{'Time':<20} {'Lat':<12} {'Lon':<12} {'Altitude':<12} {'Speed':<12} {'Distance':<10}"
    )
    print("-" * 100)

    for pos in positions:
        altitude = f"{pos['altitude_m']:.0f}m" if pos["altitude_m"] else "N/A"
        speed = f"{pos['velocity_ms'] * 3.6:.0f} km/h" if pos["velocity_ms"] else "N/A"

        print(
            f"{pos['timestamp']:<20} {pos['latitude']:<12.4f} {pos['longitude']:<12.4f} "
            f"{altitude:<12} {speed:<12} {pos['distance_from_home_km']:>8.2f} km"
        )


def main():
    """Main entry point for reader."""
    parser = argparse.ArgumentParser(
        description="LARA Flight Data Reader - Query and analyze flight data"
    )
    parser.add_argument(
        "--db", type=str, help="Path to database file (default: from config.yaml)"
    )

    args = parser.parse_args()

    # Get database path
    if args.db:
        db_path = args.db
    else:
        config = Config()
        db_path = config.db_path

    # Create reader
    try:
        reader = FlightReader(db_path)
    except Exception as e:
        print(f"❌ Error opening database: {e}")
        sys.exit(1)

    # Interactive menu loop
    try:
        while True:
            print_menu()
            choice = input("\nEnter your choice (0-10): ").strip()

            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                display_overview(reader)
            elif choice == "2":
                display_recent_flights(reader)
            elif choice == "3":
                display_top_airlines(reader)
            elif choice == "4":
                display_countries(reader)
            elif choice == "5":
                display_hourly_distribution(reader)
            elif choice == "6":
                display_altitude_distribution(reader)
            elif choice == "7":
                display_closest_flights(reader)
            elif choice == "8":
                display_daily_stats(reader)
            elif choice == "9":
                callsign = input("Enter callsign to search: ").strip()
                search_flight(reader, callsign)
            elif choice == "10":
                try:
                    flight_id = int(input("Enter flight ID: ").strip())
                    display_flight_route(reader, flight_id)
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
