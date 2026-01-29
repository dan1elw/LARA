#!/usr/bin/env python3
"""
LARA Flight Data Collector Script

Usage:
    python scripts/collect.py [--config CONFIG_FILE]
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking import Config, FlightCollector


def main():
    """Main entry point for flight collector."""
    parser = argparse.ArgumentParser(
        description="LARA Flight Data Collector - Track flights over your location"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="lara/tracking/config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(args.config)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    # Create and run collector
    try:
        collector = FlightCollector(config)
        collector.run()
    except KeyboardInterrupt:
        print("\n👋 Collector stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
