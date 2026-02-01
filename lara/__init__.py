"""
LARA - Local Air Route Analysis

A comprehensive system for tracking, analyzing, and visualizing aircraft
flight routes over your location using ADS-B data from OpenSky Network.

Components:
    - tracking: Real-time flight data collection and storage
    - analysis: Pattern detection and statistical analysis
    - visualization: Interactive map generation and dashboards

Example:
    >>> from lara.tracking import FlightCollector
    >>> from lara import Config
    >>> config = Config()
    >>> collector = FlightCollector(config)
    >>> collector.run()
"""

# Component imports for easy access
from . import tracking
from . import analysis
from . import visualization
from . import utils
from . import config

LARA_VERSION = "v1.0.0"
DB_SCHEMA_VERSION = "v1.0"

__version__ = LARA_VERSION
__author__ = "LARA Project"
__license__ = "MIT"

__all__ = [
    "tracking",
    "analysis",
    "visualization",
    "utils",
    "config",
]
