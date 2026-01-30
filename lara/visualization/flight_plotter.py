"""
Flight Path Plotter
Specialized plotting for individual flights and routes, including live tracking.
"""

import sqlite3
from .map_generator import MapGenerator


class FlightPlotter:
    """
    Plots individual flight paths on maps, including real-time live tracking.
    """

    def __init__(self, db_path: str, center_lat: float, center_lon: float):
        """
        Initialize flight plotter.

        Args:
            db_path: Path to LARA database
            center_lat: Home latitude
            center_lon: Home longitude
        """
        self.db_path = db_path
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_km = 50  # Default radius, will be read from config if available
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def plot_flight(self, flight_id: int, output_file: str):
        """
        Plot a single flight path.

        Args:
            flight_id: Flight ID
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        # Get flight info
        cursor.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
        flight = cursor.fetchone()

        if not flight:
            print(f"❌ Flight {flight_id} not found")
            return

        # Get positions
        cursor.execute(
            """
            SELECT * FROM positions 
            WHERE flight_id = ? 
            ORDER BY timestamp
        """,
            (flight_id,),
        )
        positions = [dict(row) for row in cursor.fetchall()]

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add flight path
        map_gen.add_flight_path(positions, dict(flight))

        # Add position markers
        # map_gen.add_position_markers(positions)

        # Save
        map_gen.save(output_file)

    def plot_recent_flights(
        self, hours: int = 24, output_file: str = "recent_flights.html"
    ):
        """
        Plot all recent flights.

        Args:
            hours: Number of hours to look back
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT f.*, COUNT(p.id) as position_count
            FROM flights f
            LEFT JOIN positions p ON f.id = p.flight_id
            WHERE f.first_seen >= datetime('now', ?)
            GROUP BY f.id
            HAVING position_count > 0
        """,
            (f"-{hours} hours",),
        )

        flights = cursor.fetchall()

        print(f"📍 Plotting {len(flights)} recent flights...")

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add each flight
        for flight in flights:
            cursor.execute(
                """
                SELECT * FROM positions 
                WHERE flight_id = ? 
                ORDER BY timestamp
            """,
                (flight["id"],),
            )
            positions = [dict(row) for row in cursor.fetchall()]

            map_gen.add_flight_path(positions, dict(flight))

        # Save
        map_gen.save(output_file)

    def plot_callsign(self, callsign: str, output_file: str):
        """
        Plot all occurrences of a specific callsign.

        Args:
            callsign: Flight callsign
            output_file: Output HTML filename
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT * FROM flights 
            WHERE callsign LIKE ?
            ORDER BY first_seen DESC
        """,
            (f"%{callsign}%",),
        )

        flights = cursor.fetchall()

        if not flights:
            print(f"❌ No flights found for callsign: {callsign}")
            return

        print(f"📍 Plotting {len(flights)} flights for {callsign}...")

        # Create map
        map_gen = MapGenerator(self.center_lat, self.center_lon)

        # Add each occurrence
        for flight in flights:
            cursor.execute(
                """
                SELECT * FROM positions 
                WHERE flight_id = ? 
                ORDER BY timestamp
            """,
                (flight["id"],),
            )
            positions = [dict(row) for row in cursor.fetchall()]

            map_gen.add_flight_path(positions, dict(flight))

        # Save
        map_gen.save(output_file)

    def plot_live(self, output_file: str = "live_flights.html"):
        """
        Create a live flight tracking map with real-time updates.

        This generates an HTML file with embedded JavaScript that fetches
        flight data directly from OpenSky Network API every 10 seconds.
        Uses anonymous API access (no credentials required).

        Features:
        - Auto-refresh every 10 seconds (OpenSky rate limit compliant)
        - Color-coded by altitude
        - Flight info popups
        - Loading indicators
        - Error handling for rate limits

        Args:
            output_file: Output HTML filename

        Note:
            Anonymous API access has strict rate limits (max ~100 requests/day).
            For production use, consider server-side proxying with credentials.
        """
        print(f"🔴 Generating live flight tracking map...")

        # Calculate bounding box for API query
        from lara.utils import get_bounding_box

        lat_min, lon_min, lat_max, lon_max = get_bounding_box(
            self.center_lat, self.center_lon, self.radius_km
        )

        # Generate HTML with embedded JavaScript for live updates
        html_content = self._generate_live_html(lat_min, lon_min, lat_max, lon_max)

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ Live tracking map saved to: {output_file}")
        print(f"   Updates every 10 seconds using OpenSky Network API")
        print(f"   ⚠️  Anonymous access is rate-limited (~100 requests/day)")

    def _generate_live_html(
        self, lat_min: float, lon_min: float, lat_max: float, lon_max: float
    ) -> str:
        """
        Generate complete HTML with embedded JavaScript for live tracking.

        Args:
            lat_min, lon_min, lat_max, lon_max: Bounding box coordinates

        Returns:
            Complete HTML string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>LARA Live Flight Tracking</title>
    <link rel="icon" href="../docu/icon.ico">
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossorigin=""/>
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #ffffff;
        }}
        #map {{
            position: absolute;
            top: 80px;
            left: 0;
            right: 0;
            bottom: 0;
        }}
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 80px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.8em;
            font-weight: 300;
        }}
        .status {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .status-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        .status-dot.active {{
            background: #00ff88;
        }}
        .status-dot.error {{
            background: #ff4444;
        }}
        .status-dot.loading {{
            background: #ffaa00;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        .leaflet-popup-content {{
            color: #000;
            min-width: 200px;
        }}
        .flight-info {{
            font-family: monospace;
            font-size: 0.9em;
        }}
        .flight-info strong {{
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔴 LARA Live Flight Tracking</h1>
        <div class="status">
            <div class="status-item">
                <div class="status-dot" id="status-indicator"></div>
                <span id="status-text">Initializing...</span>
            </div>
            <div class="status-item">
                <span id="flight-count">0 flights</span>
            </div>
            <div class="status-item">
                <span id="last-update">Never</span>
            </div>
        </div>
    </div>
    
    <div id="map"></div>

    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>

    <script>
        // Configuration
        const HOME_LAT = {self.center_lat};
        const HOME_LON = {self.center_lon};
        const RADIUS_KM = {self.radius_km};
        const API_URL = 'https://opensky-network.org/api/states/all';
        const UPDATE_INTERVAL = 10000; // 10 seconds (OpenSky minimum)
        
        // Bounding box
        const BOUNDS = {{
            lamin: {lat_min},
            lomin: {lon_min},
            lamax: {lat_max},
            lomax: {lon_max}
        }};

        // Initialize map
        const map = L.map('map').setView([HOME_LAT, HOME_LON], 10);
        
        // Add tile layer (light theme to match other LARA maps)
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: 'LARA Live Tracking | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19
        }}).addTo(map);

        // Add home marker
        const homeIcon = L.icon({{
            iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSIjZmYwMDAwIj48cGF0aCBkPSJNMTAgMjB2LTZoNHY2aDV2LThoM0wxMiAzbC05IDloM3Y4eiIvPjwvc3ZnPg==',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        }});
        
        L.marker([HOME_LAT, HOME_LON], {{ icon: homeIcon }})
            .bindPopup('<b>Home Location</b>')
            .addTo(map);

        // Flight markers storage
        let flightMarkers = {{}};
        let lastUpdate = null;
        let updateTimer = null;
        let isUpdating = false;

        // Status indicators
        const statusDot = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const flightCount = document.getElementById('flight-count');
        const lastUpdateEl = document.getElementById('last-update');

        function setStatus(status, text) {{
            statusDot.className = 'status-dot ' + status;
            statusText.textContent = text;
        }}

        // Altitude color mapping (matches LARA visualization)
        function getAltitudeColor(altitude) {{
            if (!altitude) return '#999999';
            if (altitude < 1000) return '#ff3b3b';      // very_low
            if (altitude < 3000) return '#ff7a18';      // low
            if (altitude < 6000) return '#f5e663';      // medium
            if (altitude < 9000) return '#00e5a8';      // high
            if (altitude < 12000) return '#00b4ff';     // very_high
            return '#7c3aed';                           // cruise
        }}

        // Haversine distance calculation
        function haversineDistance(lat1, lon1, lat2, lon2) {{
            const R = 6371; // Earth radius in km
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                      Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }}

        // Create or update flight marker
        function updateFlightMarker(state) {{
            const icao24 = state[0];
            const callsign = state[1] ? state[1].trim() : 'Unknown';
            const origin = state[2] || 'Unknown';
            const lon = state[5];
            const lat = state[6];
            const altitude = state[7] || state[13]; // baro or geo altitude
            const velocity = state[9];
            const heading = state[10];
            const onGround = state[8];

            if (!lat || !lon) return;

            // Calculate distance from home
            const distance = haversineDistance(HOME_LAT, HOME_LON, lat, lon);

            // Create plane icon with rotation
            const color = getAltitudeColor(altitude);
            const rotation = heading || 0;
            
            const planeIcon = L.divIcon({{
                className: 'plane-marker',
                html: `<div style="transform: rotate(${{rotation}}deg); width: 24px; height: 24px;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="${{color}}">
                            <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
                        </svg>
                       </div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }});

            // Create popup content
            const popupContent = `
                <div class="flight-info">
                    <strong>Callsign:</strong> ${{callsign}}<br>
                    <strong>ICAO24:</strong> ${{icao24}}<br>
                    <strong>Origin:</strong> ${{origin}}<br>
                    <strong>Altitude:</strong> ${{altitude ? Math.round(altitude) + ' m (' + Math.round(altitude * 3.28084) + ' ft)' : 'N/A'}}<br>
                    <strong>Speed:</strong> ${{velocity ? Math.round(velocity * 3.6) + ' km/h' : 'N/A'}}<br>
                    <strong>Heading:</strong> ${{heading ? Math.round(heading) + '°' : 'N/A'}}<br>
                    <strong>Distance:</strong> ${{distance.toFixed(2)}} km<br>
                    <strong>On Ground:</strong> ${{onGround ? 'Yes' : 'No'}}
                </div>
            `;

            // Update or create marker
            if (flightMarkers[icao24]) {{
                flightMarkers[icao24].setLatLng([lat, lon]);
                flightMarkers[icao24].setIcon(planeIcon);
                flightMarkers[icao24].getPopup().setContent(popupContent);
            }} else {{
                flightMarkers[icao24] = L.marker([lat, lon], {{ icon: planeIcon }})
                    .bindPopup(popupContent)
                    .addTo(map);
            }}

            flightMarkers[icao24].lastSeen = Date.now();
        }}

        // Remove stale markers
        function removeStaleMarkers() {{
            const now = Date.now();
            const staleTime = 60000; // 1 minute

            Object.keys(flightMarkers).forEach(icao24 => {{
                if (now - flightMarkers[icao24].lastSeen > staleTime) {{
                    map.removeLayer(flightMarkers[icao24]);
                    delete flightMarkers[icao24];
                }}
            }});
        }}

        // Fetch and update flights
        async function updateFlights() {{
            if (isUpdating) return;
            isUpdating = true;
            
            setStatus('loading', 'Updating...');

            try {{
                const url = `${{API_URL}}?lamin=${{BOUNDS.lamin}}&lomin=${{BOUNDS.lomin}}&lamax=${{BOUNDS.lamax}}&lomax=${{BOUNDS.lomax}}`;
                const response = await fetch(url);

                if (response.status === 429) {{
                    setStatus('error', 'Rate limited - waiting...');
                    console.warn('OpenSky API rate limit reached');
                    isUpdating = false;
                    return;
                }}

                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}`);
                }}

                const data = await response.json();
                const states = data.states || [];

                // Update all flight markers
                let visibleFlights = 0;
                states.forEach(state => {{
                    const lat = state[6];
                    const lon = state[5];
                    if (lat && lon) {{
                        const distance = haversineDistance(HOME_LAT, HOME_LON, lat, lon);
                        if (distance <= RADIUS_KM) {{
                            updateFlightMarker(state);
                            visibleFlights++;
                        }}
                    }}
                }});

                // Remove stale markers
                removeStaleMarkers();

                // Update status
                setStatus('active', 'Live');
                flightCount.textContent = `${{visibleFlights}} flight${{visibleFlights !== 1 ? 's' : ''}}`;
                
                const now = new Date();
                lastUpdateEl.textContent = now.toLocaleTimeString();
                lastUpdate = now;

            }} catch (error) {{
                console.error('Error fetching flights:', error);
                setStatus('error', 'Update failed');
            }} finally {{
                isUpdating = false;
            }}
        }}

        // Start auto-update
        function startAutoUpdate() {{
            updateFlights(); // Initial update
            updateTimer = setInterval(updateFlights, UPDATE_INTERVAL);
        }}

        // Stop auto-update
        function stopAutoUpdate() {{
            if (updateTimer) {{
                clearInterval(updateTimer);
                updateTimer = null;
            }}
        }}

        // Initialize
        console.log('LARA Live Flight Tracking initialized');
        console.log('Monitoring area:', BOUNDS);
        console.log('Update interval:', UPDATE_INTERVAL / 1000, 'seconds');
        
        startAutoUpdate();

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {{
            stopAutoUpdate();
        }});
    </script>
</body>
</html>"""

        return html

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
