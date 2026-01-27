"""
Report Generator
Creates comprehensive analysis reports in various formats.
"""

import json
from typing import Dict, Any


class ReportGenerator:
    """
    Generates analysis reports in multiple formats.
    """
    
    def generate_report(self, analysis_results: Dict[str, Any], 
                       output_path: str, format: str = 'json'):
        """
        Generate analysis report.
        
        Args:
            analysis_results: Complete analysis results
            output_path: Output file path
            format: Report format ('json', 'txt', 'html')
        """
        if format == 'json':
            self._generate_json_report(analysis_results, output_path)
        elif format == 'txt':
            self._generate_text_report(analysis_results, output_path)
        elif format == 'html':
            self._generate_html_report(analysis_results, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_json_report(self, results: Dict[str, Any], output_path: str):
        """Generate JSON report."""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    def _generate_text_report(self, results: Dict[str, Any], output_path: str):
        """Generate text report."""
        with open(output_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("LARA FLIGHT ANALYSIS REPORT\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Generated: {results['metadata']['analysis_date']}\n")
            f.write(f"Database: {results['metadata']['database']}\n\n")
            
            # Overview
            stats = results['statistics']['overview']
            f.write("OVERVIEW\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total Flights: {stats['total_flights']:,}\n")
            f.write(f"Unique Aircraft: {stats['unique_aircraft']:,}\n")
            f.write(f"Total Positions: {stats['total_positions']:,}\n\n")
            
            # Corridors
            corridors = results['corridors']
            f.write("FLIGHT CORRIDORS (Top 10)\n")
            f.write("-" * 70 + "\n")
            for corridor in corridors['corridors'][:10]:
                f.write(f"  #{corridor['rank']:2d}: ({corridor['center_lat']:.4f}, {corridor['center_lon']:.4f})\n")
                f.write(f"       Flights: {corridor['unique_flights']}, Positions: {corridor['total_positions']}\n")
            f.write("\n")
    
    def _generate_html_report(self, results: Dict[str, Any], output_path: str):
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LARA Flight Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .stat {{ background: #ecf0f1; padding: 20px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🛩️ LARA Flight Analysis Report</h1>
    <p>Generated: {results['metadata']['analysis_date']}</p>
    
    <h2>Overview Statistics</h2>
    <div class="stat">
        <p><strong>Total Flights:</strong> {results['statistics']['overview']['total_flights']:,}</p>
        <p><strong>Unique Aircraft:</strong> {results['statistics']['overview']['unique_aircraft']:,}</p>
        <p><strong>Total Positions:</strong> {results['statistics']['overview']['total_positions']:,}</p>
    </div>
    
    <h2>Top Flight Corridors</h2>
    <table>
        <tr>
            <th>Rank</th>
            <th>Position</th>
            <th>Unique Flights</th>
            <th>Total Positions</th>
            <th>Avg Altitude</th>
        </tr>
"""
        
        for corridor in results['corridors']['corridors'][:10]:
            html += f"""
        <tr>
            <td>{corridor['rank']}</td>
            <td>({corridor['center_lat']:.4f}, {corridor['center_lon']:.4f})</td>
            <td>{corridor['unique_flights']}</td>
            <td>{corridor['total_positions']}</td>
            <td>{corridor['avg_altitude_m']:.0f} m</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html)
