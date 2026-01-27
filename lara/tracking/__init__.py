"""
LARA Tracking Component

Real-time flight data collection and storage using OpenSky Network API.

Main Classes:
    - Config: Configuration management
    - FlightDatabase: SQLite database operations
    - FlightCollector: Flight data collection
    - FlightReader: Database query interface
    - OpenSkyAuth: OAuth2 authentication

Example:
    >>> from lara.tracking import Config, FlightCollector
    >>> config = Config('lara/tracking/config.yaml')
    >>> collector = FlightCollector(config)
    >>> collector.run()
"""

# Core tracking components
from .config import Config
from .database import FlightDatabase
from .collector import FlightCollector
from .reader import FlightReader
from .auth import OpenSkyAuth, OpenSkyBasicAuth, create_auth_from_config

# Utilities
from . import utils
from . import constants

__all__ = [
    # Main classes
    "Config",
    "FlightDatabase",
    "FlightCollector",
    "FlightReader",
    # Authentication
    "OpenSkyAuth",
    "OpenSkyBasicAuth",
    "create_auth_from_config",
    # Modules
    "utils",
    "constants",
]
