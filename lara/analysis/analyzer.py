"""
Main Flight Analyzer
Coordinates all analysis components.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .corridor_detector import CorridorDetector
from .pattern_matcher import PatternMatcher
from .statistics import StatisticsEngine
from .reporter import ReportGenerator
from .constants import DEFAULT_GRID_SIZE_KM, MIN_CORRIDOR_FLIGHTS


class FlightAnalyzer:
    """
    Main analyzer coordinating all analysis components.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize flight analyzer.
        
        Args:
            db_path: Path to LARA tracking database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize components
        self.corridor_detector = CorridorDetector(self.conn)
        self.pattern_matcher = PatternMatcher(self.conn)
        self.statistics = StatisticsEngine(self.conn)
        self.reporter = ReportGenerator()
    
    def analyze_all(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run complete analysis suite.
        
        Args:
            output_path: Optional path to save report
        
        Returns:
            Complete analysis results
        """
        print("\n" + "=" * 70)
        print("🔬 LARA COMPREHENSIVE ANALYSIS")
        print("=" * 70)
        
        results = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'database': self.db_path
            }
        }
        
        # Run all analyses
        print("\n📊 Running statistical analysis...")
        results['statistics'] = self.statistics.get_comprehensive_stats()
        
        print("\n🗺️  Detecting flight corridors...")
        results['corridors'] = self.corridor_detector.detect_corridors()
        
        print("\n🔍 Identifying flight patterns...")
        results['patterns'] = self.pattern_matcher.find_patterns()
        
        print("\n⏰ Analyzing temporal trends...")
        results['temporal'] = self.statistics.analyze_temporal_patterns()
        
        print("\n✈️  Analyzing airlines...")
        results['airlines'] = self.statistics.analyze_airlines()
        
        # Generate report
        if output_path:
            self.reporter.generate_report(results, output_path)
            print(f"\n💾 Report saved to: {output_path}")
        
        return results
    
    def analyze_corridors(self, grid_size_km: float) -> Dict[str, Any]:
        """Run only corridor analysis."""
        return self.corridor_detector.detect_corridors()
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Run only pattern analysis."""
        return self.pattern_matcher.find_patterns()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical summary."""
        return self.statistics.get_comprehensive_stats()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
