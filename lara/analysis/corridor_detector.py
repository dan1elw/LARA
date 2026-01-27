# """
# Flight Corridor Detection
# Identifies bidirectional flight corridors (routes used in both directions).
# """

# from typing import Dict, Any, List, Tuple
# from collections import defaultdict
# import math

# from .constants import MIN_CORRIDOR_FLIGHTS, DEFAULT_GRID_SIZE_KM, MIN_POSITIONS_FOR_CORRIDOR


# class CorridorDetector:
#     """
#     Detects bidirectional flight corridors using spatial clustering.
    
#     A corridor is defined as a spatial route used by aircraft, regardless
#     of direction. Flights going opposite directions on the same route are
#     grouped together.
#     """
    
#     def __init__(self, db_conn):
#         """
#         Initialize corridor detector.
        
#         Args:
#             db_conn: SQLite database connection
#         """
#         self.conn = db_conn
    
#     def detect_corridors(self, min_flights: int = MIN_CORRIDOR_FLIGHTS,
#                         position_tolerance_km: float = DEFAULT_GRID_SIZE_KM,
#                         min_positions: int = MIN_POSITIONS_FOR_CORRIDOR) -> Dict[str, Any]:
#         """
#         Detect bidirectional flight corridors using spatial density clustering.
        
#         Args:
#             min_flights: Minimum number of unique flights for a corridor
#             position_tolerance_km: Spatial tolerance in km for grouping positions
#             min_positions: Minimum positions per flight to consider
        
#         Returns:
#             Dictionary with corridor data
#         """
#         print(f"🔍 Detecting bidirectional flight corridors...")
#         print(f"   Position tolerance: {position_tolerance_km} km")
#         print(f"   Minimum flights: {min_flights}")
        
#         # Get ALL positions (not grouped by flight initially)
#         all_positions = self._get_all_positions(min_positions_per_flight=min_positions)
        
#         if not all_positions:
#             print("   No position data available")
#             return {'total_corridors': 0, 'corridors': []}
        
#         print(f"   Processing {len(all_positions)} total positions...")
        
#         # Grid-based spatial clustering (simpler and faster)
#         grid_clusters = self._cluster_positions_by_grid(
#             all_positions, 
#             grid_size_km=position_tolerance_km
#         )
#         print(grid_clusters)
        
#         print(f"   Found {len(grid_clusters)} spatial clusters")
        
#         # Build corridors from clusters
#         corridors = []
#         for cluster_id, cluster_positions in enumerate(grid_clusters, 1):
#             # Get unique flights in this cluster
#             unique_flights = len(set(p['flight_id'] for p in cluster_positions))
            
#             if unique_flights < min_flights:
#                 continue
            
#             corridor = self._build_corridor_from_positions(cluster_positions, cluster_id)
#             if corridor:
#                 corridors.append(corridor)
        
#         # Sort by traffic volume
#         corridors.sort(key=lambda x: x['unique_flights'], reverse=True)
        
#         # Update ranks
#         for i, corridor in enumerate(corridors, 1):
#             corridor['rank'] = i
        
#         print(f"✅ Found {len(corridors)} flight corridors (bidirectional)")
        
#         # Display top corridors
#         for corridor in corridors[:10]:
#             print(f"  #{corridor['rank']}: {corridor['unique_flights']} flights, "
#                   f"{corridor['total_positions']} positions, "
#                   f"Alt: {corridor['avg_altitude']:.0f}m")
        
#         return {
#             'total_corridors': len(corridors),
#             'corridors': corridors
#         }
    
#     def _get_all_positions(self, min_positions_per_flight: int = 10) -> List[Dict]:
#         """
#         Get all positions from all flights.
        
#         Args:
#             min_positions_per_flight: Filter out flights with too few positions
        
#         Returns:
#             List of position dictionaries
#         """
#         cursor = self.conn.cursor()
        
#         # First, get flights with enough positions
#         cursor.execute('''
#             SELECT flight_id, COUNT(*) as position_count
#             FROM positions
#             WHERE latitude IS NOT NULL AND longitude IS NOT NULL
#             GROUP BY flight_id
#             HAVING position_count >= ?
#         ''', (min_positions_per_flight,))
        
#         valid_flight_ids = [row['flight_id'] for row in cursor.fetchall()]
        
#         if not valid_flight_ids:
#             return []
        
#         # Get all positions from valid flights
#         placeholders = ','.join('?' * len(valid_flight_ids))
#         cursor.execute(f'''
#             SELECT 
#                 p.flight_id,
#                 p.latitude,
#                 p.longitude,
#                 p.altitude_m,
#                 p.heading,
#                 f.callsign
#             FROM positions p
#             JOIN flights f ON p.flight_id = f.id
#             WHERE p.flight_id IN ({placeholders})
#             AND p.latitude IS NOT NULL 
#             AND p.longitude IS NOT NULL
#         ''', valid_flight_ids)
        
#         positions = []
#         for row in cursor.fetchall():
#             positions.append({
#                 'flight_id': row['flight_id'],
#                 'lat': row['latitude'],
#                 'lon': row['longitude'],
#                 'alt': row['altitude_m'],
#                 'heading': row['heading'],
#                 'callsign': row['callsign']
#             })
        
#         return positions
    
#     def _cluster_positions_by_grid(self, positions: List[Dict], 
#                                    grid_size_km: float) -> List[List[Dict]]:
#         """
#         Cluster positions using a spatial grid.
        
#         Args:
#             positions: List of position dictionaries
#             grid_size_km: Grid cell size in kilometers
        
#         Returns:
#             List of position clusters
#         """
#         # Create grid cells
#         grid_deg = grid_size_km / 111.0  # Approximate conversion
#         grid = defaultdict(list)
        
#         for pos in positions:
#             # Assign to grid cell
#             grid_lat = round(pos['lat'] / grid_deg) * grid_deg
#             grid_lon = round(pos['lon'] / grid_deg) * grid_deg
#             cell_key = (grid_lat, grid_lon)
#             grid[cell_key].append(pos)
        
#         # Merge adjacent cells to form larger clusters
#         clusters = []
#         processed_cells = set()
        
#         for cell_key, cell_positions in grid.items():
#             if cell_key in processed_cells:
#                 continue
            
#             # Start a new cluster
#             cluster = list(cell_positions)
#             to_process = [cell_key]
#             processed_cells.add(cell_key)
            
#             # Expand cluster by checking neighbors
#             while to_process:
#                 current_cell = to_process.pop()
#                 current_lat, current_lon = current_cell
                
#                 # Check 8 neighbors
#                 for dlat in [-grid_deg, 0, grid_deg]:
#                     for dlon in [-grid_deg, 0, grid_deg]:
#                         if dlat == 0 and dlon == 0:
#                             continue
                        
#                         neighbor_key = (current_lat + dlat, current_lon + dlon)
                        
#                         if neighbor_key in grid and neighbor_key not in processed_cells:
#                             cluster.extend(grid[neighbor_key])
#                             processed_cells.add(neighbor_key)
#                             to_process.append(neighbor_key)
            
#             if cluster:
#                 clusters.append(cluster)
        
#         return clusters
    
#     def _build_corridor_from_positions(self, positions: List[Dict], 
#                                       cluster_id: int) -> Dict[str, Any]:
#         """
#         Build corridor object from clustered positions.
        
#         Args:
#             positions: List of position dictionaries
#             cluster_id: Cluster identifier
        
#         Returns:
#             Corridor dictionary or None
#         """
#         if not positions:
#             return None
        
#         # Get unique flights
#         unique_flights = set(p['flight_id'] for p in positions)
        
#         # Calculate corridor centerline using density-based path
#         corridor_points = self._calculate_corridor_path(positions)
        
#         if not corridor_points or len(corridor_points) < 2:
#             return None
        
#         # Calculate average altitude
#         altitudes = [p['alt'] for p in positions if p['alt']]
#         avg_altitude = sum(altitudes) / len(altitudes) if altitudes else 0
        
#         # Get sample callsigns
#         callsigns = list(set(p['callsign'] for p in positions if p['callsign']))
        
#         return {
#             'rank': cluster_id,
#             'unique_flights': len(unique_flights),
#             'total_positions': len(positions),
#             'avg_altitude': avg_altitude,
#             'corridor_points': corridor_points,
#             'start_point': corridor_points[0] if corridor_points else None,
#             'end_point': corridor_points[-1] if corridor_points else None,
#             'sample_callsigns': callsigns[:5]
#         }
    
#     def _calculate_corridor_path(self, positions: List[Dict]) -> List[Tuple[float, float]]:
#         """
#         Calculate the main path through a cluster of positions.
        
#         Uses Principal Component Analysis (PCA) approach to find the main axis.
        
#         Args:
#             positions: List of position dictionaries
        
#         Returns:
#             List of (lat, lon) tuples defining the corridor path
#         """
#         if not positions:
#             return []
        
#         # Extract coordinates
#         coords = [(p['lat'], p['lon']) for p in positions]
        
#         # Calculate mean center
#         mean_lat = sum(c[0] for c in coords) / len(coords)
#         mean_lon = sum(c[1] for c in coords) / len(coords)
        
#         # Center the data
#         centered = [(lat - mean_lat, lon - mean_lon) for lat, lon in coords]
        
#         # Calculate covariance matrix components
#         cov_lat_lat = sum(lat * lat for lat, lon in centered) / len(centered)
#         cov_lon_lon = sum(lon * lon for lat, lon in centered) / len(centered)
#         cov_lat_lon = sum(lat * lon for lat, lon in centered) / len(centered)
        
#         # Find principal axis (eigenvector of largest eigenvalue)
#         # For 2D, we can solve this directly
#         trace = cov_lat_lat + cov_lon_lon
#         det = cov_lat_lat * cov_lon_lon - cov_lat_lon * cov_lat_lon
        
#         # Eigenvalues
#         lambda1 = trace / 2 + math.sqrt(trace * trace / 4 - det)
        
#         # Eigenvector for lambda1
#         if abs(cov_lat_lon) > 1e-10:
#             v_lat = lambda1 - cov_lon_lon
#             v_lon = cov_lat_lon
#         else:
#             v_lat = 1
#             v_lon = 0
        
#         # Normalize
#         length = math.sqrt(v_lat * v_lat + v_lon * v_lon)
#         if length > 0:
#             v_lat /= length
#             v_lon /= length
        
#         # Project all points onto the principal axis
#         projections = []
#         for lat, lon in centered:
#             projection = lat * v_lat + lon * v_lon
#             projections.append(projection)
        
#         # Find extent along the axis
#         min_proj = min(projections)
#         max_proj = max(projections)
        
#         # Create path points along the principal axis
#         num_points = 30
#         path_points = []
        
#         for i in range(num_points + 1):
#             t = i / num_points
#             proj = min_proj + t * (max_proj - min_proj)
            
#             # Convert back to lat/lon
#             lat = mean_lat + proj * v_lat
#             lon = mean_lon + proj * v_lon
#             path_points.append((lat, lon))
        
#         return path_points
    
#     def _haversine_distance(self, lat1: float, lon1: float, 
#                            lat2: float, lon2: float) -> float:
#         """Calculate distance in km."""
#         R = 6371
#         lat1_rad = math.radians(lat1)
#         lat2_rad = math.radians(lat2)
#         dlat = math.radians(lat2 - lat1)
#         dlon = math.radians(lon2 - lon1)
        
#         a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
#         c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
#         return R * c

"""
Flight Corridor Detection
Identifies linear flight corridors using trajectory clustering.
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict
import math
import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial import distance


from .constants import DEFAULT_GRID_SIZE_KM, MIN_CORRIDOR_FLIGHTS


class CorridorDetector:
    """
    Detects linear flight corridors using trajectory-based clustering.
    
    A corridor is defined as a common linear route taken by multiple aircraft,
    identified by clustering flight paths based on their spatial similarity
    and dominant direction.
    """
    
    def __init__(self, db_conn):
        """
        Initialize corridor detector.
        
        Args:
            db_conn: SQLite database connection
        """
        self.conn = db_conn
    
    def detect_corridors(self, min_flights: int = MIN_CORRIDOR_FLIGHTS,
                        direction_tolerance: float = 10.0) -> Dict[str, Any]:
        """
        Detect linear flight corridors using trajectory clustering.
        
        Args:
            min_flights: Minimum number of unique flights for a corridor
            direction_tolerance: Angular tolerance in degrees for grouping similar directions
        
        Returns:
            Dictionary with corridor data including start/end points and directions
        """
        print(f"🔍 Detecting linear flight corridors...")
        
        # Step 1: Get all flight trajectories
        trajectories = self._get_flight_trajectories()
        
        if not trajectories:
            print("   No flight data available for corridor detection")
            return {
                'total_corridors': 0,
                'corridors': []
            }
        
        print(f"   Processing {len(trajectories)} flight trajectories...")
        
        # Step 2: Calculate trajectory characteristics
        trajectory_features = []
        trajectory_metadata = []
        
        for flight_id, positions in trajectories.items():
            if len(positions) < 2:
                continue
            
            # Calculate trajectory direction and center point
            features = self._calculate_trajectory_features(positions)
            if features:
                trajectory_features.append(features['vector'])
                trajectory_metadata.append({
                    'flight_id': flight_id,
                    'positions': positions,
                    'center_lat': features['center_lat'],
                    'center_lon': features['center_lon'],
                    'heading': features['heading'],
                    'start_point': features['start_point'],
                    'end_point': features['end_point'],
                    'avg_altitude': features['avg_altitude'],
                    'callsign': features['callsign']
                })
        
        if len(trajectory_features) < min_flights:
            print(f"   Not enough trajectories ({len(trajectory_features)}) for corridor detection")
            return {
                'total_corridors': 0,
                'corridors': []
            }
        
        # Step 3: Cluster trajectories by spatial location and direction
        print(f"   Clustering {len(trajectory_features)} trajectories...")
        clusters = self._cluster_trajectories(trajectory_features, direction_tolerance)
        
        # Step 4: Build corridor objects from clusters
        corridors = []
        corridor_rank = 1
        
        for cluster_id in set(clusters):
            if cluster_id == -1:  # Skip noise points
                continue
            
            # Get all trajectories in this cluster
            cluster_trajectories = [
                trajectory_metadata[i] 
                for i, c in enumerate(clusters) 
                if c == cluster_id
            ]
            
            if len(cluster_trajectories) < min_flights:
                continue
            
            # Build corridor from clustered trajectories
            corridor = self._build_corridor(cluster_trajectories, corridor_rank)
            corridors.append(corridor)
            corridor_rank += 1
        
        # Sort by number of flights
        corridors.sort(key=lambda x: x['unique_flights'], reverse=True)
        
        # Update ranks after sorting
        for i, corridor in enumerate(corridors, 1):
            corridor['rank'] = i
        
        print(f"✅ Found {len(corridors)} flight corridors")
        
        # Display top corridors
        for corridor in corridors[:5]:
            direction = self._heading_to_cardinal(corridor['avg_heading'])
            print(f"  #{corridor['rank']}: {corridor['unique_flights']} flights, "
                  f"Direction: {direction} ({corridor['avg_heading']:.0f}°), "
                  f"Alt: {corridor['avg_altitude']:.0f}m")
        
        return {
            'total_corridors': len(corridors),
            'corridors': corridors
        }
    
    def _get_flight_trajectories(self) -> Dict[int, List[Dict]]:
        """
        Get all flight trajectories from database.
        
        Returns:
            Dictionary mapping flight_id to list of positions
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                p.flight_id,
                p.latitude,
                p.longitude,
                p.altitude_m,
                p.heading,
                p.timestamp,
                f.callsign
            FROM positions p
            JOIN flights f ON p.flight_id = f.id
            WHERE p.latitude IS NOT NULL 
            AND p.longitude IS NOT NULL
            ORDER BY p.flight_id, p.timestamp
        ''')
        
        trajectories = defaultdict(list)
        
        for row in cursor.fetchall():
            trajectories[row['flight_id']].append({
                'lat': row['latitude'],
                'lon': row['longitude'],
                'alt': row['altitude_m'],
                'heading': row['heading'],
                'timestamp': row['timestamp'],
                'callsign': row['callsign']
            })
        
        return trajectories
    
    def _calculate_trajectory_features(self, positions: List[Dict]) -> Dict[str, Any]:
        """
        Calculate features of a trajectory for clustering.
        
        Args:
            positions: List of position dictionaries
        
        Returns:
            Dictionary with trajectory features
        """
        if len(positions) < 2:
            return None
        
        # Start and end points
        start = positions[0]
        end = positions[-1]
        
        # Calculate center point
        center_lat = sum(p['lat'] for p in positions) / len(positions)
        center_lon = sum(p['lon'] for p in positions) / len(positions)
        
        # Calculate overall heading (from start to end)
        heading = self._calculate_bearing(
            start['lat'], start['lon'],
            end['lat'], end['lon']
        )
        
        # Average altitude
        altitudes = [p['alt'] for p in positions if p['alt']]
        avg_altitude = sum(altitudes) / len(altitudes) if altitudes else 0
        
        # Create feature vector: [center_lat, center_lon, heading_x, heading_y]
        # Use heading components for directional clustering
        heading_rad = math.radians(heading)
        heading_x = math.cos(heading_rad)
        heading_y = math.sin(heading_rad)
        
        return {
            'vector': [center_lat, center_lon, heading_x * 10, heading_y * 10],  # Scale heading for clustering
            'center_lat': center_lat,
            'center_lon': center_lon,
            'heading': heading,
            'start_point': (start['lat'], start['lon']),
            'end_point': (end['lat'], end['lon']),
            'avg_altitude': avg_altitude,
            'callsign': positions[0]['callsign']
        }
    
    def _cluster_trajectories(self, features: List[List[float]], 
                             direction_tolerance: float) -> List[int]:
        """
        Cluster trajectories using DBSCAN.
        
        Args:
            features: List of feature vectors
            direction_tolerance: Angular tolerance for clustering
        
        Returns:
            List of cluster labels
        """
        # Convert to numpy array
        X = np.array(features)
        
        # Normalize features for better clustering
        # Position features (lat, lon) and direction features (heading_x, heading_y)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # DBSCAN clustering
        # eps: maximum distance between two samples for one to be considered in the neighborhood
        # min_samples: minimum number of samples in a neighborhood for a point to be core
        clustering = DBSCAN(
            eps=0.5,  # Adjust based on your data scale
            min_samples=3,
            metric='euclidean'
        )
        
        labels = clustering.fit_predict(X_scaled)
        
        return labels.tolist()
    
    def _build_corridor(self, trajectories: List[Dict], rank: int) -> Dict[str, Any]:
        """
        Build corridor object from clustered trajectories.
        
        Args:
            trajectories: List of trajectory metadata dictionaries
            rank: Corridor rank
        
        Returns:
            Corridor dictionary
        """
        # Collect all positions from all flights in corridor
        all_positions = []
        for traj in trajectories:
            all_positions.extend(traj['positions'])
        
        # Calculate corridor centerline (simplified - use average of all points)
        # In production, you might want to use more sophisticated path averaging
        corridor_points = self._calculate_corridor_centerline(trajectories)
        
        # Calculate average heading
        headings = [t['heading'] for t in trajectories]
        avg_heading = self._circular_mean(headings)
        
        # Calculate average altitude
        altitudes = [t['avg_altitude'] for t in trajectories if t['avg_altitude']]
        avg_altitude = sum(altitudes) / len(altitudes) if altitudes else 0
        
        # Get unique callsigns
        callsigns = list(set(t['callsign'] for t in trajectories if t['callsign']))
        
        return {
            'rank': rank,
            'unique_flights': len(trajectories),
            'total_positions': len(all_positions),
            'avg_heading': avg_heading,
            'avg_altitude': avg_altitude,
            'corridor_points': corridor_points,  # List of (lat, lon) defining the path
            'start_point': corridor_points[0] if corridor_points else None,
            'end_point': corridor_points[-1] if corridor_points else None,
            'sample_callsigns': callsigns[:5],  # First 5 callsigns as examples
            'direction': self._heading_to_cardinal(avg_heading)
        }
    
    def _calculate_corridor_centerline(self, trajectories: List[Dict]) -> List[Tuple[float, float]]:
        """
        Calculate centerline of corridor by averaging trajectory positions.
        
        Args:
            trajectories: List of trajectory dictionaries
        
        Returns:
            List of (lat, lon) tuples defining corridor centerline
        """
        # Simple approach: collect all start and end points, then create a line
        start_points = [t['start_point'] for t in trajectories]
        end_points = [t['end_point'] for t in trajectories]
        
        # Average start point
        avg_start_lat = sum(p[0] for p in start_points) / len(start_points)
        avg_start_lon = sum(p[1] for p in start_points) / len(start_points)
        
        # Average end point
        avg_end_lat = sum(p[0] for p in end_points) / len(end_points)
        avg_end_lon = sum(p[1] for p in end_points) / len(end_points)
        
        # Create intermediate points for smoother visualization
        points = []
        num_segments = 10
        for i in range(num_segments + 1):
            t = i / num_segments
            lat = avg_start_lat + t * (avg_end_lat - avg_start_lat)
            lon = avg_start_lon + t * (avg_end_lon - avg_start_lon)
            points.append((lat, lon))
        
        return points
    
    def _calculate_bearing(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calculate bearing between two points.
        
        Returns:
            Bearing in degrees (0-360)
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        return (bearing_deg + 360) % 360
    
    def _circular_mean(self, angles: List[float]) -> float:
        """Calculate circular mean for headings (0-360°)."""
        if not angles:
            return None
        
        sin_sum = sum(math.sin(math.radians(a)) for a in angles)
        cos_sum = sum(math.cos(math.radians(a)) for a in angles)
        
        mean_rad = math.atan2(sin_sum, cos_sum)
        mean_deg = math.degrees(mean_rad)
        
        return mean_deg if mean_deg >= 0 else mean_deg + 360
    
    def _heading_to_cardinal(self, heading: float) -> str:
        """Convert heading to cardinal direction."""
        if heading is None:
            return "Unknown"
        
        directions = [
            "N", "NNE", "NE", "ENE",
            "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW",
            "W", "WNW", "NW", "NNW"
        ]
        
        index = round(heading / 22.5) % 16
        return directions[index]
