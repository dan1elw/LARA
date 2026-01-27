"""
Tests for reporting.
"""

import json
import pytest
from lara.analysis.reporter import ReportGenerator


@pytest.fixture
def sample_results():
    return {
        "metadata": {
            "analysis_date": "2024-01-01",
            "database": "test_db",
        },
        "statistics": {
            "overview": {
                "total_flights": 12345,
                "unique_aircraft": 321,
                "total_positions": 987654,
            }
        },
        "corridors": {
            "corridors": [
                {
                    "rank": 1,
                    "center_lat": 51.5074,
                    "center_lon": -0.1278,
                    "unique_flights": 100,
                    "total_positions": 5000,
                    "avg_altitude_m": 11000,
                },
                {
                    "rank": 2,
                    "center_lat": 48.8566,
                    "center_lon": 2.3522,
                    "unique_flights": 80,
                    "total_positions": 4000,
                    "avg_altitude_m": 10500,
                },
            ]
        },
    }


class ReportTester():
    """Tests for ReportGenerator class."""

    def test_generate_json_report(tmp_path, sample_results):
        """Test JSON report generation."""
        output_file = tmp_path / "report.json"
        generator = ReportGenerator()

        generator.generate_report(sample_results, output_file, format="json")

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert data["metadata"]["database"] == "test_db"
        assert data["statistics"]["overview"]["total_flights"] == 12345


    def test_generate_text_report(tmp_path, sample_results):
        """Test text report generation."""
        output_file = tmp_path / "report.txt"
        generator = ReportGenerator()

        generator.generate_report(sample_results, output_file, format="txt")

        assert output_file.exists()

        content = output_file.read_text()

        assert "LARA FLIGHT ANALYSIS REPORT" in content
        assert "Total Flights: 12,345" in content
        assert "FLIGHT CORRIDORS (Top 10)" in content
        assert "# 1:" in content


    def test_generate_html_report(tmp_path, sample_results):
        """Test HTML report generation."""
        output_file = tmp_path / "report.html"
        generator = ReportGenerator()

        generator.generate_report(sample_results, output_file, format="html")

        assert output_file.exists()

        content = output_file.read_text()

        assert "<title>LARA Flight Analysis Report</title>" in content
        assert "🛩️ LARA Flight Analysis Report" in content
        assert "(51.5074, -0.1278)" in content
        assert "11000 m" in content


    def test_unsupported_format_raises_error(tmp_path, sample_results):
        """Test that unsupported format raises ValueError."""
        output_file = tmp_path / "report.xyz"
        generator = ReportGenerator()

        with pytest.raises(ValueError, match="Unsupported format"):
            generator.generate_report(sample_results, output_file, format="xml")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
