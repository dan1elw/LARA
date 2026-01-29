"""
Tests for map generator.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.visualization.map_generator import MapGenerator


class TestMapGenerator:
    """Tests for MapGenerator class."""

    def test_init(self):
        """Test map generator initialization."""
        gen = MapGenerator(49.3508, 8.1364)
        assert gen.center_lat == 49.3508
        assert gen.center_lon == 8.1364
        assert gen.map is not None

    def test_custom_style(self):
        """Test custom map style."""
        gen = MapGenerator(49.3508, 8.1364, style="CartoDB.Positron")
        assert gen.style == "CartoDB.Positron"

    def test_add_flight_path(self):
        """Test adding flight path."""
        gen = MapGenerator(49.3508, 8.1364)

        positions = [
            {"latitude": 49.35, "longitude": 8.14, "altitude_m": 10000},
            {"latitude": 49.36, "longitude": 8.15, "altitude_m": 10100},
            {"latitude": 49.37, "longitude": 8.16, "altitude_m": 10200},
        ]

        flight_info = {"callsign": "TEST123", "icao24": "abc123"}

        gen.add_flight_path(positions, flight_info)
        # Should not raise exception

    def test_add_corridor(self):
        """Test adding corridor."""
        gen = MapGenerator(49.3508, 8.1364)

        corridor = {
            'heading': 90,
            'length_km': 49.35,
            'width_km': 8.14,
            'center_lat': 49.35,
            'center_lon': 8.14,
            'unique_flights': 50,
            'total_positions': 1000,
            'avg_altitude_m': 10000
        }

        gen.add_corridor(corridor, rank=1)
        # Should not raise exception

    def test_save_map(self):
        """Test saving map to file."""
        gen = MapGenerator(49.3508, 8.1364)

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            gen.save(temp_path)
            assert Path(temp_path).exists()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_altitude_color(self):
        """Test altitude color assignment."""
        gen = MapGenerator(49.3508, 8.1364)

        # Test different altitudes
        assert gen._get_altitude_color(500) is not None
        assert gen._get_altitude_color(5000) is not None
        assert gen._get_altitude_color(15000) is not None

    def test_rank_color(self):
        """Test rank color assignment."""
        gen = MapGenerator(49.3508, 8.1364)

        # Test different ranks
        color1 = gen._get_rank_color(1)
        color2 = gen._get_rank_color(2)
        assert color1 is not None
        assert color2 is not None
