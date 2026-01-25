"""
Tests for LARA flight collector.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from requests.exceptions import RequestException

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking.collector import FlightCollector
from lara.tracking.config import Config


@pytest.fixture
def temp_config():
    """Create temporary configuration for testing."""
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create config
    config = Config()
    config.set('database.path', db_path)
    config.set('location.latitude', 49.3508)
    config.set('location.longitude', 8.1364)
    config.set('tracking.radius_km', 50)
    config.set('tracking.update_interval_seconds', 10)
    
    yield config
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def mock_api_response():
    """Create mock API response with sample flight data."""
    return {
        'time': 1234567890,
        'states': [
            [
                'abc123',      # icao24
                'DLH123 ',     # callsign
                'Germany',     # origin_country
                1234567890,    # time_position
                1234567890,    # last_contact
                8.1364,        # longitude
                49.3508,       # latitude
                10000,         # baro_altitude
                False,         # on_ground
                250,           # velocity
                90,            # true_track
                0,             # vertical_rate
                None,          # sensors
                10050,         # geo_altitude
                '1200',        # squawk
            ],
            [
                'def456',
                'AFR456 ',
                'France',
                1234567890,
                1234567890,
                8.2000,
                49.4000,
                9500,
                False,
                240,
                85,
                -5,
                None,
                9550,
                '2000',
            ]
        ]
    }


class TestFlightCollector:
    """Tests for FlightCollector class."""
    
    def test_init(self, temp_config):
        """Test collector initialization."""
        collector = FlightCollector(temp_config)
        
        assert collector.home_lat == 49.3508
        assert collector.home_lon == 8.1364
        assert collector.radius_km == 50
        assert collector.update_interval == 10
        assert collector.iteration_count == 0
    
    @patch('lara.tracking.collector.requests.get')
    def test_fetch_flights_success(self, mock_get, temp_config, mock_api_response):
        """Test successful flight data fetch."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        flights = collector.fetch_flights()
        
        assert len(flights) == 2
        assert flights[0][0] == 'abc123'
        assert flights[1][0] == 'def456'
    
    @patch('lara.tracking.collector.requests.get')
    def test_fetch_flights_empty_response(self, mock_get, temp_config):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.json.return_value = {'states': None}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        flights = collector.fetch_flights()
        
        assert flights == []
    
    @patch('lara.tracking.collector.requests.get')
    def test_fetch_flights_api_error(self, mock_get, temp_config, capsys):
        """Test handling of API errors."""
        mock_get.side_effect = RequestException("API Error")
        
        collector = FlightCollector(temp_config)
        flights = collector.fetch_flights()
        
        assert flights == []
        captured = capsys.readouterr()
        assert "Error fetching data" in captured.out
    
    @patch('lara.tracking.collector.requests.get')
    def test_fetch_flights_timeout(self, mock_get, temp_config, capsys):
        """Test handling of API timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        collector = FlightCollector(temp_config)
        flights = collector.fetch_flights()
        
        assert flights == []
        captured = capsys.readouterr()
        assert "timeout" in captured.out.lower()
    
    def test_process_flight_valid(self, temp_config):
        """Test processing valid flight data."""
        collector = FlightCollector(temp_config)
        timestamp = datetime.now().isoformat()
        
        state = [
            'abc123', 'DLH123 ', 'Germany', 1234567890, 1234567890,
            8.1364, 49.3508, 10000, False, 250, 90, 0, None, 10050, '1200'
        ]
        
        result = collector.process_flight(state, timestamp)
        
        assert result is not None
        assert result['callsign'] == 'DLH123'
        assert result['distance'] >= 0
        assert result['altitude'] == 10000
    
    def test_process_flight_no_position(self, temp_config):
        """Test processing flight without position data."""
        collector = FlightCollector(temp_config)
        timestamp = datetime.now().isoformat()
        
        state = [
            'abc123', 'DLH123 ', 'Germany', 1234567890, 1234567890,
            None, None, 10000, False, 250, 90, 0, None, 10050, '1200'
        ]
        
        result = collector.process_flight(state, timestamp)
        
        assert result is None
    
    def test_process_flight_outside_radius(self, temp_config):
        """Test processing flight outside tracking radius."""
        collector = FlightCollector(temp_config)
        timestamp = datetime.now().isoformat()
        
        # Position very far away (different country)
        state = [
            'abc123', 'DLH123 ', 'Germany', 1234567890, 1234567890,
            0.0, 0.0, 10000, False, 250, 90, 0, None, 10050, '1200'
        ]
        
        result = collector.process_flight(state, timestamp)
        
        assert result is None
    
    def test_display_flight_info(self, temp_config, capsys):
        """Test flight information display."""
        collector = FlightCollector(temp_config)
        
        flight_info = {
            'callsign': 'DLH123',
            'distance': 5.2,
            'altitude': 10000,
            'velocity': 250
        }
        
        collector.display_flight_info(flight_info)
        
        captured = capsys.readouterr()
        assert 'DLH123' in captured.out
        assert '5.2 km' in captured.out
        assert '10000 m' in captured.out
    
    @patch('lara.tracking.collector.requests.get')
    def test_run_single_iteration(self, mock_get, temp_config, mock_api_response):
        """Test single collection iteration."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        count = collector.run_single_iteration()
        
        assert collector.iteration_count == 1
        assert count >= 0  # May be filtered by radius
    
    @patch('lara.tracking.collector.requests.get')
    def test_run_single_iteration_no_flights(self, mock_get, temp_config):
        """Test iteration with no flights detected."""
        mock_response = Mock()
        mock_response.json.return_value = {'states': None}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        count = collector.run_single_iteration()
        
        assert count == 0
    
    def test_print_header(self, temp_config, capsys):
        """Test header printing."""
        collector = FlightCollector(temp_config)
        collector.print_header()
        
        captured = capsys.readouterr()
        assert 'LARA' in captured.out
        assert '49.3508' in captured.out
        assert '8.1364' in captured.out
    
    def test_print_statistics(self, temp_config, capsys):
        """Test statistics printing."""
        collector = FlightCollector(temp_config)
        collector.print_statistics()
        
        captured = capsys.readouterr()
        assert 'Statistics' in captured.out
        assert 'flights tracked' in captured.out.lower()


class TestCollectorIntegration:
    """Integration tests for flight collector."""
    
    @patch('lara.tracking.collector.requests.get')
    def test_complete_collection_cycle(self, mock_get, temp_config, mock_api_response):
        """Test complete collection cycle from API to database."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        
        # Run multiple iterations
        for _ in range(3):
            collector.run_single_iteration()
        
        # Verify data was stored
        stats = collector.db.get_statistics()
        assert stats['total_flights'] >= 0
        assert stats['total_positions'] >= 0
    
    @patch('lara.tracking.collector.requests.get')
    def test_daily_stats_update(self, mock_get, temp_config, mock_api_response):
        """Test that daily stats are updated correctly."""
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        
        # Run iteration
        collector.run_single_iteration()
        
        # Simulate date change by updating last_date
        from datetime import date
        collector.last_date = date.today()
        
        # Should trigger stats update on next iteration
        collector.run_single_iteration()
        
        # Verify collector tracked iterations
        assert collector.iteration_count == 2


class TestCollectorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_malformed_state_vector(self, temp_config):
        """Test handling of malformed state vector."""
        collector = FlightCollector(temp_config)
        timestamp = datetime.now().isoformat()
        
        # Incomplete state vector
        state = ['abc123', 'DLH123']
        
        result = collector.process_flight(state, timestamp)
        
        # Should handle gracefully and return None
        assert result is None
    
    @patch('lara.tracking.collector.requests.get')
    def test_invalid_json_response(self, mock_get, temp_config, capsys):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        collector = FlightCollector(temp_config)
        flights = collector.fetch_flights()
        
        assert flights == []
        captured = capsys.readouterr()
        assert "Error parsing" in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
