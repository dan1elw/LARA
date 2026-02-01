"""
Tests for live flight tracking feature in FlightPlotter.

This test suite covers:
- Live tracking HTML generation
- Bounding box calculation integration
- JavaScript configuration embedding
- HTML structure validation
- Error handling
- File output
"""

import pytest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.visualization.flight_plotter import FlightPlotter


@pytest.fixture
def plotter_db():
    """Create sample database for plotter testing."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE flights (
            id INTEGER PRIMARY KEY,
            callsign TEXT,
            first_seen TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE positions (
            id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            latitude REAL,
            longitude REAL,
            altitude_m REAL,
            timestamp TIMESTAMP
        )
    """)

    # Insert test data
    cursor.execute("""
        INSERT INTO flights (id, callsign, first_seen)
        VALUES (1, 'TEST123', datetime('now'))
    """)

    for i in range(5):
        cursor.execute(
            """
            INSERT INTO positions (flight_id, latitude, longitude, altitude_m, timestamp)
            VALUES (1, ?, ?, 10000, datetime('now'))
        """,
            (49.35 + i * 0.01, 8.14 + i * 0.01),
        )

    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def plotter(plotter_db):
    """Create FlightPlotter instance."""
    plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)
    yield plotter
    plotter.close()


class TestLiveTrackingHTMLGeneration:
    """Tests for live tracking HTML generation."""

    def test_generate_live_html_structure(self, plotter):
        """Test that generated HTML has correct structure."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

        # Required meta tags
        assert '<meta charset="utf-8"' in html
        assert "viewport" in html

        # Title
        assert "<title>LARA Live Flight Tracking</title>" in html

        # Favicon
        assert "icon.ico" in html

    def test_generate_live_html_includes_leaflet(self, plotter):
        """Test that Leaflet library is included."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Leaflet CSS
        assert "leaflet.css" in html
        assert "unpkg.com/leaflet" in html

        # Leaflet JavaScript
        assert "leaflet.js" in html

        # Integrity hashes for security
        assert "integrity=" in html
        assert "crossorigin=" in html

    def test_generate_live_html_includes_map_element(self, plotter):
        """Test that map container element is present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        assert '<div id="map">' in html

    def test_generate_live_html_includes_status_indicators(self, plotter):
        """Test that status UI elements are present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Header
        assert '<div class="header">' in html
        assert "LARA Live Flight Tracking" in html

        # Status indicators
        assert 'id="status-indicator"' in html
        assert 'id="status-text"' in html
        assert 'id="flight-count"' in html
        assert 'id="last-update"' in html

    def test_generate_live_html_embeds_coordinates(self, plotter):
        """Test that coordinates are embedded in JavaScript."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Home coordinates
        assert f"HOME_LAT = {plotter.center_lat}" in html
        assert f"HOME_LON = {plotter.center_lon}" in html
        assert f"RADIUS_KM = {plotter.radius_km}" in html

        # Bounding box
        assert "lamin: 49.0" in html
        assert "lomin: 8.0" in html
        assert "lamax: 50.0" in html
        assert "lomax: 9.0" in html

    def test_generate_live_html_includes_api_url(self, plotter):
        """Test that OpenSky API URL is included."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        assert "API_URL = 'https://opensky-network.org/api/states/all'" in html

    def test_generate_live_html_includes_update_interval(self, plotter):
        """Test that update interval is configured."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # 10 seconds = 10000 milliseconds
        assert "UPDATE_INTERVAL = 10000" in html

    def test_generate_live_html_includes_javascript_functions(self, plotter):
        """Test that required JavaScript functions are present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Core functions
        assert "function setStatus" in html
        assert "function getAltitudeColor" in html
        assert "function haversineDistance" in html
        assert "function updateFlightMarker" in html
        assert "function removeStaleMarkers" in html
        assert "function updateFlights" in html
        assert "function startAutoUpdate" in html
        assert "function stopAutoUpdate" in html

    def test_generate_live_html_includes_altitude_colors(self, plotter):
        """Test that altitude color scheme matches LARA visualization."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Color codes should match constants
        assert "#ff3b3b" in html  # very_low
        assert "#ff7a18" in html  # low
        assert "#f5e663" in html  # medium
        assert "#00e5a8" in html  # high
        assert "#00b4ff" in html  # very_high
        assert "#7c3aed" in html  # cruise

    def test_generate_live_html_includes_error_handling(self, plotter):
        """Test that error handling code is present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Rate limit handling
        assert "response.status === 429" in html
        assert "Rate limited" in html

        # Error handling
        assert "try {" in html
        assert "catch (error)" in html
        assert "console.error" in html

    def test_generate_live_html_includes_home_marker(self, plotter):
        """Test that home location marker is configured."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        assert "homeIcon" in html
        assert "Home Location" in html
        assert "L.marker([HOME_LAT, HOME_LON]" in html

    def test_generate_live_html_includes_plane_icon(self, plotter):
        """Test that plane icon SVG is present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # SVG path for plane icon
        assert "M21 16v-2l-8-5V3.5" in html  # Plane path
        assert "transform: rotate" in html  # Rotation for heading

    def test_generate_live_html_includes_css_styling(self, plotter):
        """Test that CSS styling is present."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        assert "<style>" in html
        assert "</style>" in html

        # Key styles
        assert "body {" in html
        assert "#map {" in html
        assert ".header {" in html
        assert ".status {" in html
        assert "@keyframes pulse" in html

    def test_generate_live_html_valid_javascript(self, plotter):
        """Test that JavaScript syntax is valid (basic checks)."""
        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        # Check balanced braces in script sections
        script_start = html.find("<script>")
        script_end = html.rfind("</script>")
        script_content = html[script_start:script_end]

        # Count braces
        open_braces = script_content.count("{")
        close_braces = script_content.count("}")

        assert open_braces == close_braces, "Unbalanced braces in JavaScript"

        # Check for common syntax patterns
        assert "const " in script_content
        assert "function " in script_content
        assert "async function" in script_content


class TestPlotLiveMethod:
    """Tests for the plot_live method."""

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_plot_live_creates_file(self, mock_bbox, plotter):
        """Test that plot_live creates output file."""
        mock_bbox.return_value = (49.0, 8.0, 50.0, 9.0)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            plotter.plot_live(temp_path)

            # File should exist
            assert Path(temp_path).exists()

            # File should have content
            assert Path(temp_path).stat().st_size > 0

            # Should be valid HTML
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "<!DOCTYPE html>" in content
                assert "LARA Live Flight Tracking" in content

        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_plot_live_uses_bounding_box(self, mock_bbox, plotter):
        """Test that plot_live calculates bounding box correctly."""
        mock_bbox.return_value = (48.5, 7.5, 49.5, 8.5)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            plotter.plot_live(temp_path)

            # Should have called get_bounding_box with correct parameters
            mock_bbox.assert_called_once_with(
                plotter.center_lat, plotter.center_lon, plotter.radius_km
            )

            # Bounding box should be in generated HTML
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "lamin: 48.5" in content
                assert "lomin: 7.5" in content
                assert "lamax: 49.5" in content
                assert "lomax: 8.5" in content

        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_plot_live_default_filename(self, mock_bbox, plotter, capsys):
        """Test plot_live with default filename."""
        mock_bbox.return_value = (49.0, 8.0, 50.0, 9.0)

        try:
            plotter.plot_live()

            # Default file should be created
            assert Path("live_flights.html").exists()

            # Check console output
            captured = capsys.readouterr()
            assert "live_flights.html" in captured.out
            assert "10 seconds" in captured.out

        finally:
            Path("live_flights.html").unlink(missing_ok=True)

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_plot_live_console_output(self, mock_bbox, plotter, capsys):
        """Test that plot_live provides informative console output."""
        mock_bbox.return_value = (49.0, 8.0, 50.0, 9.0)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            plotter.plot_live(temp_path)

            captured = capsys.readouterr()

            # Should show progress
            assert "Generating live flight tracking" in captured.out

            # Should show output location
            assert temp_path in captured.out

            # Should mention update interval
            assert "10 seconds" in captured.out

            # Should warn about rate limits
            assert "rate-limited" in captured.out.lower()

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestLiveTrackingConfiguration:
    """Tests for configuration and customization."""

    def test_custom_radius_reflected_in_html(self, plotter_db):
        """Test that custom radius is reflected in generated HTML."""
        plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)
        plotter.radius_km = 100  # Custom radius

        html = plotter._generate_live_html(49.0, 8.0, 50.0, 9.0)

        assert "RADIUS_KM = 100" in html

        plotter.close()

    def test_different_coordinates(self, plotter_db):
        """Test with different home coordinates."""
        plotter = FlightPlotter(plotter_db, 52.5200, 13.4050)  # Berlin

        html = plotter._generate_live_html(52.0, 13.0, 53.0, 14.0)

        assert "HOME_LAT = 52.52" in html
        assert "HOME_LON = 13.405" in html

        plotter.close()


class TestLiveTrackingEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_plot_live_with_invalid_path(self, mock_bbox, plotter):
        """Test handling of invalid output path."""
        mock_bbox.return_value = (49.0, 8.0, 50.0, 9.0)

        with pytest.raises((OSError, PermissionError)):
            plotter.plot_live("/nonexistent/directory/file.html")

    def test_generate_live_html_with_extreme_coordinates(self, plotter):
        """Test with extreme coordinate values."""
        # Near poles
        html = plotter._generate_live_html(85.0, -170.0, 89.0, 170.0)

        assert "lamin: 85.0" in html
        assert "lomin: -170.0" in html

    def test_generate_live_html_with_zero_coordinates(self, plotter):
        """Test with zero coordinates (equator/prime meridian)."""
        html = plotter._generate_live_html(-1.0, -1.0, 1.0, 1.0)

        assert "lamin: -1.0" in html
        assert "lomin: -1.0" in html


class TestLiveTrackingIntegration:
    """Integration tests for live tracking feature."""

    @patch("lara.visualization.flight_plotter.get_bounding_box")
    def test_complete_live_tracking_workflow(self, mock_bbox, plotter):
        """Test complete workflow from database to HTML."""
        mock_bbox.return_value = (49.0, 8.0, 50.0, 9.0)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            # Generate live map
            plotter.plot_live(temp_path)

            # Verify file exists and has content
            assert Path(temp_path).exists()

            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify it's a complete, valid HTML document
            assert content.startswith("<!DOCTYPE html>")
            assert content.endswith("</html>")

            # Verify all required components are present
            assert "Leaflet" in content
            assert "OpenSky" in content
            assert "updateFlights" in content
            assert "startAutoUpdate" in content

            # Verify coordinates from plotter instance
            assert str(plotter.center_lat) in content
            assert str(plotter.center_lon) in content

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestBackwardCompatibility:
    """Tests to ensure existing functionality still works."""

    def test_existing_methods_unchanged(self, plotter):
        """Test that existing methods still work after adding plot_live."""
        # These should not raise exceptions
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            temp_path = f.name

        try:
            plotter.plot_flight(1, temp_path)
            assert Path(temp_path).exists()
        except Exception as e:
            # Flight not found is okay, method should work
            assert "not found" in str(e).lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_plotter_initialization_unchanged(self, plotter_db):
        """Test that FlightPlotter initialization still works."""
        plotter = FlightPlotter(plotter_db, 49.3508, 8.1364)

        assert plotter.db_path == plotter_db
        assert plotter.center_lat == 49.3508
        assert plotter.center_lon == 8.1364
        assert plotter.conn is not None

        plotter.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
