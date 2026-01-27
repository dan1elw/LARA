"""
Interactive Dashboard
Creates comprehensive visualization dashboard.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any

from .map_generator import MapGenerator
from .flight_plotter import FlightPlotter
from .heatmap_generator import HeatmapGenerator


class Dashboard:
    """
    Creates comprehensive visualization dashboard.
    """
    
    def __init__(self, db_path: str, center_lat: float, center_lon: float,
                 output_dir: str = 'visualizations'):
        """
        Initialize dashboard.
        
        Args:
            db_path: Path to LARA database
            center_lat: Home latitude
            center_lon: Home longitude
            output_dir: Output directory for visualizations
        """
        self.db_path = db_path
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def generate_complete_dashboard(self, analysis_results: Dict[str, Any] = None):
        """
        Generate complete visualization dashboard.
        
        Args:
            analysis_results: Optional analysis results from lara.analysis
        """
        print("\n" + "=" * 70)
        print("🗺️  GENERATING VISUALIZATION DASHBOARD")
        print("=" * 70)
        
        # 1. Corridor map
        print("\n1. Generating corridor map...")
        self._generate_corridor_map(analysis_results)
        
        # 2. Traffic heatmap
        print("\n2. Generating traffic heatmap...")
        heatmap = HeatmapGenerator(self.db_path, self.center_lat, self.center_lon)
        heatmap.generate_traffic_heatmap(
            str(self.output_dir / 'traffic_heatmap.html')
        )
        heatmap.close()
        
        # 3. Recent flights
        print("\n3. Generating recent flights map...")
        plotter = FlightPlotter(self.db_path, self.center_lat, self.center_lon)
        plotter.plot_recent_flights(
            hours=24,
            output_file=str(self.output_dir / 'recent_flights_24h.html')
        )
        plotter.close()
        
        # 4. Altitude heatmap
        print("\n4. Generating altitude heatmap...")
        heatmap = HeatmapGenerator(self.db_path, self.center_lat, self.center_lon)
        heatmap.generate_altitude_heatmap(
            str(self.output_dir / 'altitude_heatmap.html')
        )
        heatmap.close()
        
        # 5. Generate index page
        print("\n5. Generating dashboard index...")
        self._generate_index_page()
        
        print("\n" + "=" * 70)
        print(f"✅ Dashboard generated in: {self.output_dir}")
        print("=" * 70)
        print(f"\nOpen: {self.output_dir / 'index.html'}")
    
    def _generate_corridor_map(self, analysis_results: Dict[str, Any] = None):
        """Generate corridor visualization map."""
        map_gen = MapGenerator(self.center_lat, self.center_lon)
        
        if analysis_results and 'corridors' in analysis_results:
            corridors = analysis_results['corridors'].get('corridors', [])
            
            for corridor in corridors[:20]:  # Top 20
                map_gen.add_corridor(corridor, corridor['rank'])
        else:
            # Fallback: query from database
            from lara.analysis import FlightAnalyzer
            analyzer = FlightAnalyzer(self.db_path)
            result = analyzer.analyze_corridors()
            analyzer.close()
            
            for corridor in result['corridors'][:20]:
                map_gen.add_corridor(corridor, corridor['rank'])
        
        map_gen.save(str(self.output_dir / 'corridors.html'))
    
    def _generate_index_page(self):
        """Generate HTML index page for dashboard."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>LARA Dashboard</title>
    <link rel="icon" href="../docu/icon.ico">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: #1a1a1a;
            color: #ffffff;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .header h1 {
            margin: 0;
            font-size: 3em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        .container {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        .card {
            background: #2a2a2a;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4);
        }
        .card h2 {
            margin: 0 0 15px 0;
            color: #667eea;
            font-size: 1.5em;
        }
        .card p {
            margin: 0;
            opacity: 0.8;
            line-height: 1.6;
        }
        .card .icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        .btn {
            display: inline-block;
            margin-top: 15px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #764ba2;
        }
        .footer {
            text-align: center;
            padding: 40px 20px;
            opacity: 0.6;
            margin-top: 60px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛩️ LARA Dashboard</h1>
        <p>Local Air Route Analysis</p>
    </div>
    
    <div class="container">
        <div class="grid">
            <div class="card" onclick="window.location='corridors.html'">
                <div class="icon">🗺️</div>
                <h2>Flight Corridors</h2>
                <p>Visualize the most common flight paths and corridors over your location. Sized by traffic volume.</p>
                <a href="corridors.html" class="btn">View Map</a>
            </div>
            
            <div class="card" onclick="window.location='traffic_heatmap.html'">
                <div class="icon">🔥</div>
                <h2>Traffic Heatmap</h2>
                <p>Density heatmap showing areas with highest flight activity. Darker areas indicate more traffic.</p>
                <a href="traffic_heatmap.html" class="btn">View Heatmap</a>
            </div>
            
            <div class="card" onclick="window.location='recent_flights_24h.html'">
                <div class="icon">✈️</div>
                <h2>Recent Flights (24h)</h2>
                <p>All flights detected in the last 24 hours with complete flight paths and position data.</p>
                <a href="recent_flights_24h.html" class="btn">View Flights</a>
            </div>
            
            <div class="card" onclick="window.location='altitude_heatmap.html'">
                <div class="icon">📊</div>
                <h2>Altitude Analysis</h2>
                <p>Heatmap weighted by altitude. Shows where aircraft fly lowest (potential noise impact).</p>
                <a href="altitude_heatmap.html" class="btn">View Analysis</a>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>LARA - Local Air Route Analysis<br>
        Data visualization powered by Folium & OpenStreetMap</p>
    </div>
</body>
</html>
"""
        
        with open(self.output_dir / 'index.html', 'w') as f:
            f.write(html)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
