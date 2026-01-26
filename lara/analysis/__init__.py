"""
LARA Analysis Component

Advanced analytics and pattern detection for flight data.

Main Classes:
    - FlightAnalyzer: Main coordinator for all analyses
    - CorridorDetector: Spatial clustering and corridor identification
    - PatternMatcher: Recurring flight and schedule detection
    - StatisticsEngine: Comprehensive statistical analysis
    - ReportGenerator: Multi-format report generation

Example:
    >>> from lara.analysis import FlightAnalyzer
    >>> analyzer = FlightAnalyzer('data/lara_flights.db')
    >>> results = analyzer.analyze_all(output_path='report.json')
    >>> analyzer.close()
"""

# Main analysis components
from .analyzer import FlightAnalyzer
from .corridor_detector import CorridorDetector
from .pattern_matcher import PatternMatcher
from .statistics import StatisticsEngine
from .reporter import ReportGenerator

# Utilities
from . import constants

__all__ = [
    # Main classes
    'FlightAnalyzer',
    'CorridorDetector',
    'PatternMatcher',
    'StatisticsEngine',
    'ReportGenerator',
    
    # Modules
    'constants',
]
