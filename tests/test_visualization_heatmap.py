"""
Tests for heatmap generator.
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.visualization.heatmap_generator import HeatmapGenerator


@pytest.fixture
def heatmap_db():
    """Create sample database for heatmap testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            distance_from_home_km REAL
        )
    ''')
    
    # Insert positions
    for i in range(20):
        cursor.execute('''
            INSERT INTO positions (latitude, longitude, altitude_m, distance_from_home_km)
            VALUES (?, ?, ?, ?)
        ''', (49.35 + i * 0.01, 8.14 + i * 0.01, 10000, i * 2.0))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestHeatmapGenerator:
    """Tests for HeatmapGenerator class."""
    
    def test_init(self, heatmap_db):
        """Test heatmap generator initialization."""
        heatmap = HeatmapGenerator(heatmap_db, 49.3508, 8.1364)
        assert heatmap.db_path == heatmap_db
        assert heatmap.conn is not None
        heatmap.close()
    
    def test_generate_traffic_heatmap(self, heatmap_db):
        """Test traffic heatmap generation."""
        heatmap = HeatmapGenerator(heatmap_db, 49.3508, 8.1364)
        
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            temp_path = f.name
        
        try:
            heatmap.generate_traffic_heatmap(temp_path)
            assert Path(temp_path).exists()
        finally:
            heatmap.close()
            Path(temp_path).unlink(missing_ok=True)
    
    def test_generate_altitude_heatmap(self, heatmap_db):
        """Test altitude heatmap generation."""
        heatmap = HeatmapGenerator(heatmap_db, 49.3508, 8.1364)
        
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            temp_path = f.name
        
        try:
            heatmap.generate_altitude_heatmap(temp_path)
            assert Path(temp_path).exists()
        finally:
            heatmap.close()
            Path(temp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
