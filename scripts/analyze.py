#!/usr/bin/env python3
"""
LARA Flight Data Analysis Script

Usage:
    python scripts/analyze.py [--db DATABASE_FILE] [--output OUTPUT_FILE] [--format FORMAT]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking import Config
from lara.analysis import FlightAnalyzer


def main(config_path: str = "data/config.yaml"):
    """Main entry point for analyzer."""
    parser = argparse.ArgumentParser(
        description="LARA Flight Data Analyzer - Advanced pattern analysis"
    )
    parser.add_argument(
        "--db", type=str, help="Path to database file (default: from config.yaml)"
    )
    parser.add_argument(
        "--output", type=str, help="Output file for report (default: auto-generated)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "txt", "html"],
        default="json",
        help="Report format (default: json)",
    )
    parser.add_argument(
        "--corridors-only", action="store_true", help="Run only corridor analysis"
    )
    parser.add_argument(
        "--patterns-only", action="store_true", help="Run only pattern analysis"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Run only statistical analysis"
    )
    parser.add_argument(
        "--grid-size",
        type=float,
        default=5.0,
        help="Grid size in km for corridor analysis (default: 5.0)",
    )

    args = parser.parse_args()

    # Get database path
    if args.db:
        db_path = args.db
    else:
        config = Config(config_path)
        db_path = config.db_path

    # Create output filename
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"data/lara_analysis_{timestamp}.{args.format}"

    # Create analyzer
    try:
        analyzer = FlightAnalyzer(db_path)
    except Exception as e:
        print(f"❌ Error opening database: {e}")
        sys.exit(1)

    try:
        if args.corridors_only:
            # Run only corridor analysis
            results = analyzer.analyze_corridors(grid_size_km=args.grid_size)
            print("\n✅ Corridor analysis complete!")

        elif args.patterns_only:
            # Run only pattern analysis
            results = analyzer.analyze_patterns()
            print("\n✅ Pattern analysis complete!")

        elif args.stats_only:
            # Run only statistical analysis
            results = analyzer.get_statistics()
            print("\n✅ Statistical analysis complete!")

        else:
            # Run full analysis
            _ = analyzer.analyze_all(output_path=args.output)
            print(f"\n✅ Complete analysis saved to: {args.output}")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
