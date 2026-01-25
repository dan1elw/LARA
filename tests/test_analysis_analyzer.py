"""
Tests for main analyzer.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.analysis import FlightAnalyzer


@pytest.fixture
def full_db():
    """Create full database for analyzer testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create COMPLETE schema matching tracking component
    cursor.execute('''
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY,
            icao24 TEXT,
            callsign TEXT,
            origin_country TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            min_distance_km REAL,
            max_altitude_m REAL,
            min_altitude_m REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            heading REAL,
            distance_from_home_km REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    try:
        os.unlink(db_path)
    except:
        pass


class TestFlightAnalyzer:
    """Tests for FlightAnalyzer class."""
    
    def test_init(self, full_db):
        """Test analyzer initialization."""
        analyzer = FlightAnalyzer(full_db)
        assert analyzer.db_path == full_db
        assert analyzer.corridor_detector is not None
        assert analyzer.pattern_matcher is not None
        assert analyzer.statistics is not None
        analyzer.close()
    
    def test_analyze_corridors(self, full_db):
        """Test corridor analysis method."""
        analyzer = FlightAnalyzer(full_db)
        result = analyzer.analyze_corridors(grid_size_km=5.0)
        
        assert 'total_corridors' in result
        analyzer.close()
    
    def test_analyze_patterns(self, full_db):
        """Test pattern analysis method."""
        analyzer = FlightAnalyzer(full_db)
        result = analyzer.analyze_patterns()
        
        assert 'recurring_flights' in result
        analyzer.close()
    
    def test_get_statistics(self, full_db):
        """Test statistics method."""
        analyzer = FlightAnalyzer(full_db)
        result = analyzer.get_statistics()
        
        assert 'overview' in result
        analyzer.close()
    
    def test_analyze_all(self, full_db):
        """Test complete analysis."""
        analyzer = FlightAnalyzer(full_db)
        
        # Create temp output file
        fd, output_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        
        try:
            result = analyzer.analyze_all(output_path=output_path)
            
            assert 'metadata' in result
            assert 'statistics' in result
            assert 'corridors' in result
            assert 'patterns' in result
            
            # Check file was created
            assert os.path.exists(output_path)
        finally:
            analyzer.close()
            try:
                os.unlink(output_path)
            except:
                pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
