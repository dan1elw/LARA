#!/usr/bin/env python3
"""
LARA Visualization Script

Usage:
    python scripts/visualize.py [OPTIONS]

Examples:
    # Generate complete dashboard
    python scripts/visualize.py --dashboard

    # Plot single flight
    python scripts/visualize.py --flight 123 --output flight_123.html

    # Plot recent flights
    python scripts/visualize.py --recent 24 --output recent.html

    # Generate traffic heatmap
    python scripts/visualize.py --heatmap --output heatmap.html

    # Plot specific callsign
    python scripts/visualize.py --callsign DLH123 --output dlh123.html
"""

import sys
import argparse
import webbrowser
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.config import Config
from lara.visualization import MapGenerator, FlightPlotter, HeatmapGenerator, Dashboard
from lara.analysis import FlightAnalyzer


def main():
    """Main entry point for visualization."""
    parser = argparse.ArgumentParser(
        description="LARA Flight Visualizer - Create interactive maps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate complete dashboard:
    python3 scripts/visualize.py --dashboard
    
  Plot single flight:
    python3 scripts/visualize.py --flight 123
    
  Plot recent flights:
    python3 scripts/visualize.py --recent 24
    
  Generate heatmap:
    python3 scripts/visualize.py --heatmap
    
  Plot specific callsign:
    python3 scripts/visualize.py --callsign DLH123
        """,
    )

    # Database options
    parser.add_argument(
        "--config",
        type=str,
        default="data/config.yaml",
        help="Path to config file (default: data/config.yaml)",
    )
    parser.add_argument(
        "--db",
        type=str,
        help="Path to database file (default: from config.yaml)",
    )

    # Visualization type
    viz_group = parser.add_mutually_exclusive_group()
    viz_group.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate complete visualization dashboard",
    )
    viz_group.add_argument(
        "--flight",
        type=int,
        metavar="FLIGHT_ID",
        help="Plot single flight by ID",
    )
    viz_group.add_argument(
        "--recent",
        type=int,
        metavar="HOURS",
        help="Plot flights from last N hours",
    )
    viz_group.add_argument(
        "--heatmap",
        action="store_true",
        help="Generate traffic density heatmap",
    )
    viz_group.add_argument(
        "--live",
        action="store_true",
        help="Generate live flight tracking map"
    )
    viz_group.add_argument(
        "--altitude-heatmap",
        action="store_true",
        help="Generate altitude-weighted heatmap",
    )
    viz_group.add_argument(
        "--callsign",
        type=str,
        metavar="CALLSIGN",
        help="Plot all flights with specific callsign",
    )
    viz_group.add_argument(
        "--corridors",
        action="store_true",
        help="Visualize flight corridors from analysis",
    )

    # Output options
    parser.add_argument(
        "--output", type=str, help="Output filename (default: auto-generated)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="visualizations",
        help="Output directory for dashboard (default: visualizations)",
    )

    # Map options
    parser.add_argument(
        "--style",
        type=str,
        choices=["CartoDB.DarkMatter", "CartoDB.Positron", "OpenStreetMap"],
        default="CartoDB.DarkMatter",
        help="Map style (default: CartoDB.DarkMatter)",
    )
    parser.add_argument(
        "--zoom", type=int, default=10, help="Initial zoom level (default: 10)"
    )

    args = parser.parse_args()

    # Load configuration
    config = Config(args.config)

    # Get database path
    db_path = args.db if args.db else config.db_path

    # Get home coordinates
    center_lat = config.home_latitude
    center_lon = config.home_longitude

    try:
        if args.dashboard:
            # Generate complete dashboard
            print("\n🗺️  Generating complete visualization dashboard...")

            # Run analysis first
            print("\n📊 Running analysis...")
            analyzer = FlightAnalyzer(db_path)
            analysis_results = analyzer.analyze_all()
            analyzer.close()

            # Generate visualizations
            dashboard = Dashboard(db_path, center_lat, center_lon, args.output_dir)
            dashboard.generate_complete_dashboard(analysis_results)
            dashboard.close()

            # open the dashboard in default web browser
            index_path = Path(args.output_dir) / "index.html"
            webbrowser.open(index_path.resolve().as_uri())

        elif args.flight:
            # Plot single flight
            output = args.output or f"flight_{args.flight}.html"
            plotter = FlightPlotter(db_path, center_lat, center_lon)
            plotter.plot_flight(args.flight, output)
            plotter.close()

        elif args.recent:
            # Plot recent flights
            output = args.output or f"recent_{args.recent}h.html"
            plotter = FlightPlotter(db_path, center_lat, center_lon)
            plotter.plot_recent_flights(args.recent, output)
            plotter.close()

        elif args.live:
            # Plot live flights
            output = args.output or "live_flights.html"
            plotter = FlightPlotter(db_path, center_lat, center_lon)
            plotter.plot_live(output)
            plotter.close()

        elif args.heatmap:
            # Generate traffic heatmap
            output = args.output or "traffic_heatmap.html"
            heatmap = HeatmapGenerator(db_path, center_lat, center_lon)
            heatmap.generate_traffic_heatmap(output)
            heatmap.close()

        elif args.altitude_heatmap:
            # Generate altitude heatmap
            output = args.output or "altitude_heatmap.html"
            heatmap = HeatmapGenerator(db_path, center_lat, center_lon)
            heatmap.generate_altitude_heatmap(output)
            heatmap.close()

        elif args.callsign:
            # Plot specific callsign
            output = args.output or f"{args.callsign.lower()}.html"
            plotter = FlightPlotter(db_path, center_lat, center_lon)
            plotter.plot_callsign(args.callsign, output)
            plotter.close()

        elif args.corridors:
            # Visualize corridors
            output = args.output or "corridors.html"

            print("📊 Analyzing corridors...")
            analyzer = FlightAnalyzer(db_path)
            corridor_data = analyzer.analyze_corridors()
            analyzer.close()

            print("🗺️  Generating corridor map...")
            map_gen = MapGenerator(center_lat, center_lon, args.zoom, args.style)

            for corridor in corridor_data["corridors"][:20]:
                map_gen.add_corridor(corridor, corridor["rank"])

            map_gen.save(output)

        else:
            # No option specified, show help
            parser.print_help()
            sys.exit(1)

    except FileNotFoundError:
        print(f"❌ Database not found: {db_path}")
        print("   Run the collector first: python scripts/collect.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Visualize dashboard for testing
    sys.argv = ["scripts/visualize.py", "--dashboard", "--config", "docu/example/config.yaml", "--output-dir", "docu/example/html/"]
    main()
