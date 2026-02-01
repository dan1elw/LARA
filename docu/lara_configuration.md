# LARA Configuration Guide

Complete guide to configuring the Local Air Route Analysis (LARA) system.

---

## Table of Contents

1. [Configuration File Structure](#configuration-file-structure)
2. [Location Settings](#location-settings)
3. [Tracking Settings](#tracking-settings)
4. [Database Settings](#database-settings)
5. [API Settings](#api-settings)
6. [Analysis Parameters](#analysis-parameters)
7. [Visualization Settings](#visualization-settings)
8. [Advanced Configuration](#advanced-configuration)
9. [Examples](#examples)

---

## Configuration File Structure

LARA uses YAML configuration files to customize its behavior. The configuration is organized into logical sections:

```yaml
location:          # Where to track flights
tracking:          # How to collect data
database:          # Where to store data
api:              # API authentication
```

If no configuration file is provided, LARA uses defaults centered on Berlin, Germany.

---

## Location Settings

Define the geographic center point for flight tracking.

### Parameters

| Parameter   | Type   | Required | Description                          | Example              |
|-------------|--------|----------|--------------------------------------|----------------------|
| `latitude`  | float  | Yes      | Home latitude in degrees (-90 to 90) | 50.114              |
| `longitude` | float  | Yes      | Home longitude in degrees (-180 to 180) | 8.679            |
| `name`      | string | No       | Descriptive location name            | "Frankfurt a. M., Germany" |

### Example

```yaml
location:
  latitude: 50.114
  longitude: 8.679
  name: "Frankfurt am Main, Germany"
```

### Validation

- Latitude must be between -90° and 90°
- Longitude must be between -180° and 180°
- If validation fails, defaults to Berlin (52.516257°N, 13.377525°E)

---

## Tracking Settings

Control how flight data is collected from the OpenSky Network API.

### Parameters

| Parameter                  | Type  | Required | Description                              | Default | Range        |
|----------------------------|-------|----------|------------------------------------------|---------|--------------|
| `radius_km`                | float | Yes      | Tracking radius around home location (km)| 25      | > 0          |
| `update_interval_seconds`  | int   | No       | Seconds between API requests             | 15      | ≥ 10         |

### Example

```yaml
tracking:
  radius_km: 50
  update_interval_seconds: 15
```

### Important Notes

- **Minimum interval**: OpenSky Network rate limits require ≥10 second intervals for anonymous users
- **Authenticated users**: OAuth2 authentication allows higher request rates
- **Radius recommendations**: 
  - Urban areas: 25-50 km
  - Rural areas: 50-100 km
  - Maximum practical: ~200 km (API bounding box limits)

---

## Database Settings

Specify where flight data is stored.

### Parameters

| Parameter | Type   | Required | Description                    | Example                     |
|-----------|--------|----------|--------------------------------|-----------------------------|
| `path`    | string | Yes      | SQLite database file path      | "data/lara_flights.db"      |

### Example

```yaml
database:
  path: "data/lara_flights_berlin.db"
```

### Notes

- Directory will be created automatically if it doesn't exist
- Uses SQLite format (no server required)
- File can grow large with extended tracking (plan disk space accordingly)

---

## API Settings

Configure authentication with OpenSky Network API.

### Parameters

| Parameter          | Type   | Required | Description                              | Example               |
|--------------------|--------|----------|------------------------------------------|-----------------------|
| `credentials_path` | string | No       | Path to OAuth2 credentials.json file     | "credentials.json"    |

### Example

```yaml
api:
  credentials_path: "credentials.json"
```

### Authentication Modes

1. **Anonymous** (no credentials)
   - Rate limit: ~100 requests/day
   - Recommended interval: ≥15 seconds
   - No registration required

2. **OAuth2** (with credentials)
   - Higher rate limits
   - Recommended interval: ≥10 seconds
   - Requires OpenSky Network account

### Getting OAuth2 Credentials

1. Create account at https://opensky-network.org/
2. Navigate to: My Account → API Client
3. Download `credentials.json`
4. Place in your LARA directory
5. Update config with path to credentials file

---

## Analysis Parameters

Advanced settings that control corridor detection, pattern matching, and statistical analysis. These are defined as constants in `config.py` and typically don't need modification.

### Corridor Detection

| Parameter                  | Default | Description                                      |
|----------------------------|---------|--------------------------------------------------|
| `HEADING_TOLERANCE_DEG`    | 20.0    | Angular tolerance for grouping flights (±degrees)|
| `PROXIMITY_THRESHOLD_KM`   | 10.0    | Maximum distance to group positions (km)         |
| `MIN_CORRIDOR_LENGTH_KM`   | 3.0     | Minimum corridor length to detect (km)           |
| `MIN_LINEARITY_SCORE`      | 0.3     | Minimum quality score (0-1, higher=straighter)   |
| `MIN_FLIGHTS_FOR_CORRIDOR` | 60      | Minimum flights to qualify as corridor           |

**When to adjust:**
- **Urban areas**: Decrease `PROXIMITY_THRESHOLD_KM` to 5-7 km
- **Rural areas**: Increase `MIN_CORRIDOR_LENGTH_KM` to 5-10 km
- **Low traffic**: Decrease `MIN_FLIGHTS_FOR_CORRIDOR` to 30-40

### Pattern Detection

| Parameter                   | Default | Description                                    |
|-----------------------------|---------|------------------------------------------------|
| `MIN_PATTERN_OCCURRENCES`   | 5       | Minimum repetitions to identify pattern        |
| `ROUTE_SIMILARITY_THRESHOLD`| 0.8     | Route similarity threshold (0-1)               |

### Temporal Analysis

| Parameter                | Default | Description                              |
|--------------------------|---------|------------------------------------------|
| `PEAK_HOUR_THRESHOLD`    | 0.7     | Traffic threshold for peak hours (0-1)   |
| `DAYS_FOR_TREND_ANALYSIS`| 30      | Historical days to analyze               |

---

## Visualization Settings

Control map appearance and styling.

### Map Style

| Parameter         | Default            | Options                                    |
|-------------------|--------------------|--------------------------------------------|
| `DEFAULT_MAP_STYLE` | CartoDB.Positron | CartoDB.Positron, CartoDB.DarkMatter, OpenStreetMap |
| `DEFAULT_ZOOM`    | 10                 | 1 (world) to 18 (street level)             |

### Flight Paths

| Parameter            | Default | Description                          |
|----------------------|---------|--------------------------------------|
| `FLIGHT_PATH_WEIGHT` | 2       | Line thickness (pixels)              |
| `FLIGHT_PATH_OPACITY`| 0.6     | Transparency (0=invisible, 1=opaque) |

### Corridors

| Parameter              | Default | Description                          |
|------------------------|---------|--------------------------------------|
| `CORRIDOR_OPACITY`     | 0.3     | Overlay transparency                 |
| `CORRIDOR_BORDER_WEIGHT` | 2     | Border line thickness                |

### Color Schemes

Defined in `Colors` class:

- **Altitude colors**: Height-based color coding (red=low, purple=high)
- **Rank colors**: Traffic volume visualization (red=most, blue=least)
- **Heatmap gradient**: Density visualization (neon plasma theme)

---

## Advanced Configuration

### Constants

Physical constants (in `Constants` class) should **NOT** be modified:

```python
EARTH_RADIUS_KM = 6371.0      # Earth's radius
METERS_TO_FEET = 3.28084      # Unit conversion
MS_TO_KMH = 3.6               # Unit conversion
KM_PER_DEGREE_LAT = 111.32    # Geodetic constant
```

### Modifying Settings

To modify analysis settings, edit the `Settings` class in `config.py`:

```python
class Settings:
    MIN_FLIGHTS_FOR_CORRIDOR: int = 40  # Changed from 60
    HEADING_TOLERANCE_DEG: float = 15.0  # Changed from 20.0
    ...
```

### Using Config in Code

```python
from lara.config import Config, Settings, Constants

# Load configuration
config = Config('config.yaml')

# Access location
print(f"Tracking: {config.location_name}")
print(f"Center: {config.home_latitude}°N, {config.home_longitude}°E")
print(f"Radius: {config.radius_km} km")

# Access settings
min_flights = Settings.MIN_FLIGHTS_FOR_CORRIDOR
tolerance = Settings.HEADING_TOLERANCE_DEG

# Access constants
earth_radius = Constants.EARTH_RADIUS_KM
```

---

## Examples

### Example 1: Frankfurt Airport

Track flights around Frankfurt International Airport with high precision:

```yaml
location:
  latitude: 50.0379
  longitude: 8.5622
  name: "Frankfurt Airport (FRA), Germany"

tracking:
  radius_km: 30
  update_interval_seconds: 10

database:
  path: "data/frankfurt_flights.db"

api:
  credentials_path: "credentials.json"  # OAuth2 for higher rate limits
```

### Example 2: Rural Monitoring

Track flights over a rural area with longer intervals:

```yaml
location:
  latitude: 49.3508
  longitude: 8.1364
  name: "Neustadt an der Weinstraße"

tracking:
  radius_km: 75
  update_interval_seconds: 20

database:
  path: "data/rural_flights.db"

api:
  credentials_path: null  # Anonymous mode
```

### Example 3: City Center

Monitor urban airspace with OAuth2 authentication:

```yaml
location:
  latitude: 51.5074
  longitude: -0.1278
  name: "London, UK"

tracking:
  radius_km: 40
  update_interval_seconds: 12

database:
  path: "data/london_flights.db"

api:
  credentials_path: "opensky_credentials.json"
```

### Example 4: Minimal Configuration

Rely on defaults (Berlin, Germany):

```yaml
location:
  latitude: 52.516257
  longitude: 13.377525

tracking:
  radius_km: 25

database:
  path: "data/lara_flights.db"
```

---

## Configuration Validation

LARA validates your configuration when loaded:

### Valid Configuration
```
✅ Configuration loaded successfully
   Location: Berlin, Germany
   Tracking radius: 25 km
```

### Invalid Configuration
```
⚠️  Warning: Invalid config structure, using defaults
   Location: Berlin, Germany (default)
```

Common validation failures:
- Missing required fields (`latitude`, `longitude`, `radius_km`, `path`)
- Invalid coordinates (latitude not in -90 to 90, longitude not in -180 to 180)
- Invalid types (string where number expected)
- Negative or zero radius

---

## Best Practices

1. **Start with defaults**: Use the default configuration and adjust as needed
2. **Test OAuth2**: Verify credentials work with `python -m lara.tracking.auth credentials.json`
3. **Choose appropriate radius**: Larger radius = more flights but more API load
4. **Respect rate limits**: Keep intervals ≥10s (anonymous) or ≥10s (authenticated)
5. **Plan disk space**: Database grows ~1-5 MB per day depending on traffic
6. **Version control**: Keep your config.yaml in version control (without credentials)
7. **Separate credentials**: Store credentials.json separately, not in version control

---

## Troubleshooting

### Problem: "Rate limited by OpenSky Network (429)"
**Solution**: Increase `update_interval_seconds` or set up OAuth2 authentication

### Problem: "Invalid config structure, using defaults"
**Solution**: Check YAML syntax, ensure all required fields are present

### Problem: "No flights detected"
**Solution**: 
- Increase `radius_km`
- Verify location coordinates are correct
- Check OpenSky Network status
- or just wait ...

### Problem: "Database file growing too large"
**Solution**: 
- Reduce `radius_km`
- Increase `update_interval_seconds`
- Periodically archive old data

---

## Configuration File Location

LARA searches for configuration in this order:

1. Path provided to `Config(config_path='...')`
2. `data/config.yaml` (default)
3. Built-in defaults

Recommended structure:
```
your-project/
├── data/
│   ├── config.yaml
│   ├── credentials.json  (git-ignored)
│   └── lara_flights.db
├── scripts/
│   ├── collect.py
│   └── visualize.py
└── lara/
    └── config.py
```

---

## Summary

| Configuration Aspect | Required | Default      | Typical Range      |
|----------------------|----------|--------------|-------------------|
| Latitude             | Yes      | 52.52°N      | -90° to 90°       |
| Longitude            | Yes      | 13.38°E      | -180° to 180°     |
| Radius (km)          | Yes      | 25           | 10-200            |
| Update interval (s)  | No       | 15           | 10-60             |
| Database path        | Yes      | data/...db   | Any valid path    |
| OAuth2 credentials   | No       | None         | credentials.json  |

For most users, only **location**, **radius**, and optionally **credentials** need to be configured. All other settings have sensible defaults.