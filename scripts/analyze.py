#!/usr/bin/env python3
"""
LARA Flight Data Analysis Script

Advanced analysis and pattern detection for flight routes.

Usage:
    python scripts/analyze.py [--db DATABASE_FILE] [--output OUTPUT_DIR]
"""

import sys
import argparse
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tracking import Config, FlightReader
from tracking.utils import haversine_distance


class FlightAnalyzer:
    """Advanced flight data analysis."""
    
    def __init__(self, db_path: str):
        """
        Initialize analyzer.
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.reader = FlightReader(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close connections."""
        self.reader.close()
        self.conn.close()
    
    def analyze_flight_corridors(self, grid_size_km: float = 5.0) -> dict:
        """
        Identify common flight corridors using grid-based clustering.
        
        Args:
            grid_size_km: Size of grid cells in kilometers
        
        Returns:
            Dictionary with corridor analysis results
        """
        print(f"\n🗺️  Analyzing Flight Corridors (Grid size: {grid_size_km} km)")
        print("=" * 70)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT latitude, longitude, altitude_m
            FROM positions
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ''')
        
        # Grid-based clustering
        grid = defaultdict(lambda: {'count': 0, 'altitudes': []})
        
        for row in cursor.fetchall():
            lat, lon, alt = row['latitude'], row['longitude'], row['altitude_m']
            
            # Round to grid
            grid_lat = round(lat / (grid_size_km / 111.0)) * (grid_size_km / 111.0)
            grid_lon = round(lon / (grid_size_km / 111.0)) * (grid_size_km / 111.0)
            
            key = (grid_lat, grid_lon)
            grid[key]['count'] += 1
            if alt:
                grid[key]['altitudes'].append(alt)
        
        # Find top corridors
        sorted_corridors = sorted(grid.items(), key=lambda x: x[1]['count'], reverse=True)
        
        top_corridors = []
        for i, (coords, data) in enumerate(sorted_corridors[:10], 1):
            avg_alt = sum(data['altitudes']) / len(data['altitudes']) if data['altitudes'] else 0
            
            corridor = {
                'rank': i,
                'center_lat': coords[0],
                'center_lon': coords[1],
                'flight_count': data['count'],
                'avg_altitude_m': avg_alt
            }
            top_corridors.append(corridor)
            
            print(f"{i:2d}. Position ({coords[0]:.4f}, {coords[1]:.4f})")
            print(f"    Flights: {data['count']:,} | Avg Altitude: {avg_alt:.0f} m")
        
        return {
            'grid_size_km': grid_size_km,
            'total_cells': len(grid),
            'top_corridors': top_corridors
        }
    
    def analyze_peak_hours(self) -> dict:
        """
        Analyze peak traffic hours with detailed breakdown.
        
        Returns:
            Dictionary with hourly analysis
        """
        print(f"\n⏰ Peak Traffic Hours Analysis")
        print("=" * 70)
        
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
        
        hourly_data = []
        max_count = 0
        
        for row in cursor.fetchall():
            data = {
                'hour': row['hour'],
                'flight_count': row['flight_count'],
                'avg_distance_km': row['avg_distance'],
                'avg_altitude_m': row['avg_altitude']
            }
            hourly_data.append(data)
            max_count = max(max_count, row['flight_count'])
        
        # Identify peak hours
        peak_threshold = max_count * 0.7
        peak_hours = [d for d in hourly_data if d['flight_count'] >= peak_threshold]
        
        print("\nHourly Distribution:")
        for data in hourly_data:
            bar_length = int((data['flight_count'] / max_count) * 40) if max_count > 0 else 0
            bar = '█' * bar_length
            peak_marker = " 🔥" if data['flight_count'] >= peak_threshold else ""
            print(f"{data['hour']:02d}:00 | {bar:<40} {data['flight_count']:>4}{peak_marker}")
        
        print(f"\nPeak Hours (≥70% of max):")
        for data in peak_hours:
            print(f"  {data['hour']:02d}:00 - {data['flight_count']} flights")
        
        return {
            'hourly_data': hourly_data,
            'peak_hours': [d['hour'] for d in peak_hours],
            'busiest_hour': max(hourly_data, key=lambda x: x['flight_count']) if hourly_data else None
        }
    
    def analyze_airline_patterns(self) -> dict:
        """
        Analyze patterns by airline/operator.
        
        Returns:
            Dictionary with airline analysis
        """
        print(f"\n✈️  Airline Pattern Analysis")
        print("=" * 70)
        
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
            HAVING flight_count > 5
            ORDER BY flight_count DESC
            LIMIT 20
        ''')
        
        airlines = []
        for row in cursor.fetchall():
            airline_data = {
                'code': row['airline_code'],
                'flight_count': row['flight_count'],
                'avg_min_distance_km': row['avg_min_distance'],
                'avg_altitude_m': row['avg_altitude'],
                'closest_approach_km': row['closest_approach']
            }
            airlines.append(airline_data)
            
            print(f"{row['airline_code']:4s} | {row['flight_count']:4d} flights | "
                  f"Avg Dist: {row['avg_min_distance']:5.1f} km | "
                  f"Avg Alt: {row['avg_altitude']:6.0f} m | "
                  f"Closest: {row['closest_approach']:5.1f} km")
        
        return {'airlines': airlines}
    
    def analyze_altitude_patterns(self) -> dict:
        """
        Analyze altitude distribution and patterns.
        
        Returns:
            Dictionary with altitude analysis
        """
        print(f"\n📊 Altitude Pattern Analysis")
        print("=" * 70)
        
        cursor = self.conn.cursor()
        
        # Overall altitude stats
        cursor.execute('''
            SELECT 
                MIN(altitude_m) as min_alt,
                MAX(altitude_m) as max_alt,
                AVG(altitude_m) as avg_alt,
                COUNT(*) as total_positions
            FROM positions
            WHERE altitude_m IS NOT NULL
        ''')
        
        stats = cursor.fetchone()
        
        print(f"Altitude Statistics:")
        print(f"  Minimum: {stats['min_alt']:.0f} m ({stats['min_alt'] * 3.28084:.0f} ft)")
        print(f"  Maximum: {stats['max_alt']:.0f} m ({stats['max_alt'] * 3.28084:.0f} ft)")
        print(f"  Average: {stats['avg_alt']:.0f} m ({stats['avg_alt'] * 3.28084:.0f} ft)")
        
        # Low-altitude flights (potential approach/departure)
        cursor.execute('''
            SELECT COUNT(DISTINCT flight_id) as count
            FROM positions
            WHERE altitude_m < 3000
        ''')
        low_alt_flights = cursor.fetchone()['count']
        
        print(f"\nLow-Altitude Flights (<3000m): {low_alt_flights}")
        
        # Altitude by distance (are closer flights lower?)
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN distance_from_home_km < 10 THEN '0-10 km'
                    WHEN distance_from_home_km < 20 THEN '10-20 km'
                    WHEN distance_from_home_km < 30 THEN '20-30 km'
                    ELSE '30+ km'
                END as distance_range,
                AVG(altitude_m) as avg_altitude,
                COUNT(*) as count
            FROM positions
            WHERE altitude_m IS NOT NULL
            GROUP BY distance_range
            ORDER BY distance_from_home_km
        ''')
        
        print(f"\nAltitude by Distance:")
        distance_patterns = []
        for row in cursor.fetchall():
            pattern = {
                'distance_range': row['distance_range'],
                'avg_altitude_m': row['avg_altitude'],
                'sample_count': row['count']
            }
            distance_patterns.append(pattern)
            print(f"  {row['distance_range']:10s}: {row['avg_altitude']:6.0f} m avg ({row['count']} samples)")
        
        return {
            'min_altitude_m': stats['min_alt'],
            'max_altitude_m': stats['max_alt'],
            'avg_altitude_m': stats['avg_alt'],
            'low_altitude_flights': low_alt_flights,
            'distance_patterns': distance_patterns
        }
    
    def analyze_temporal_trends(self, days: int = 30) -> dict:
        """
        Analyze temporal trends over time.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dictionary with temporal analysis
        """
        print(f"\n📅 Temporal Trends (Last {days} days)")
        print("=" * 70)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                DATE(first_seen) as date,
                COUNT(*) as flight_count,
                AVG(min_distance_km) as avg_distance,
                COUNT(DISTINCT SUBSTR(callsign, 1, 3)) as unique_airlines
            FROM flights
            WHERE first_seen >= date('now', ?)
            GROUP BY DATE(first_seen)
            ORDER BY date
        ''', (f'-{days} days',))
        
        daily_trends = []
        total_flights = 0
        
        print("\nDaily Flight Activity:")
        for row in cursor.fetchall():
            trend = {
                'date': row['date'],
                'flight_count': row['flight_count'],
                'avg_distance_km': row['avg_distance'],
                'unique_airlines': row['unique_airlines']
            }
            daily_trends.append(trend)
            total_flights += row['flight_count']
            
            print(f"{row['date']} | {row['flight_count']:4d} flights | "
                  f"{row['unique_airlines']:3d} airlines | "
                  f"Avg dist: {row['avg_distance']:5.1f} km")
        
        avg_daily = total_flights / len(daily_trends) if daily_trends else 0
        
        print(f"\nAverage daily flights: {avg_daily:.1f}")
        
        # Weekday analysis
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
            WHERE first_seen >= date('now', ?)
            GROUP BY strftime('%w', first_seen)
            ORDER BY CAST(strftime('%w', first_seen) AS INTEGER)
        ''', (f'-{days} days',))
        
        print(f"\nWeekday Distribution:")
        weekday_data = []
        for row in cursor.fetchall():
            weekday_info = {
                'weekday': row['weekday'],
                'flight_count': row['flight_count']
            }
            weekday_data.append(weekday_info)
            print(f"  {row['weekday']:9s}: {row['flight_count']:4d} flights")
        
        return {
            'daily_trends': daily_trends,
            'avg_daily_flights': avg_daily,
            'weekday_distribution': weekday_data
        }
    
    def generate_summary_report(self, output_file: str = None) -> dict:
        """
        Generate comprehensive summary report.
        
        Args:
            output_file: Optional file path to save JSON report
        
        Returns:
            Complete analysis dictionary
        """
        print("\n" + "=" * 70)
        print("📋 GENERATING COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 70)
        
        # Get overview
        overview = self.reader.get_overview()
        
        # Run all analyses
        corridors = self.analyze_flight_corridors()
        peak_hours = self.analyze_peak_hours()
        airlines = self.analyze_airline_patterns()
        altitudes = self.analyze_altitude_patterns()
        trends = self.analyze_temporal_trends()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'overview': overview,
            'flight_corridors': corridors,
            'peak_hours': peak_hours,
            'airline_patterns': airlines,
            'altitude_patterns': altitudes,
            'temporal_trends': trends
        }
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Report saved to: {output_file}")
        
        return report


def main():
    """Main entry point for analyzer."""
    parser = argparse.ArgumentParser(
        description='LARA Flight Data Analyzer - Advanced pattern analysis'
    )
    parser.add_argument(
        '--db',
        type=str,
        help='Path to database file (default: from config.yaml)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for JSON report (optional)'
    )
    parser.add_argument(
        '--corridors-only',
        action='store_true',
        help='Run only corridor analysis'
    )
    parser.add_argument(
        '--grid-size',
        type=float,
        default=5.0,
        help='Grid size in km for corridor analysis (default: 5.0)'
    )
    
    args = parser.parse_args()
    
    # Get database path
    if args.db:
        db_path = args.db
    else:
        config = Config()
        db_path = config.db_path
    
    # Create analyzer
    try:
        analyzer = FlightAnalyzer(db_path)
    except Exception as e:
        print(f"❌ Error opening database: {e}")
        sys.exit(1)
    
    try:
        if args.corridors_only:
            # Run only corridor analysis
            analyzer.analyze_flight_corridors(grid_size_km=args.grid_size)
        else:
            # Run full analysis
            output_file = args.output or f"data/lara_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            analyzer.generate_summary_report(output_file)
        
        print("\n✅ Analysis complete!")
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
