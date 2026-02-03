# OpenSky Network API Documentation

## Overview

The OpenSky Network is a community-based receiver network that collects air traffic surveillance data. It provides free REST API access to real-time and historical flight data collected from ADS-B (Automatic Dependent Surveillance-Broadcast) transponders on aircraft worldwide.

## API Endpoints

### Main Endpoint: All State Vectors

```
GET https://opensky-network.org/api/states/all
```

This endpoint returns the current state vectors (position, velocity, altitude, etc.) of all aircraft visible to the OpenSky Network.

### Parameters

- **`time`** (optional): Unix timestamp (seconds) to retrieve historical data
- **`icao24`** (optional): ICAO 24-bit address to filter for specific aircraft
- **`lamin`, `lomin`, `lamax`, `lomax`** (optional): Bounding box coordinates
  - `lamin`: Minimum latitude (decimal degrees)
  - `lomin`: Minimum longitude (decimal degrees)
  - `lamax`: Maximum latitude (decimal degrees)
  - `lomax`: Maximum longitude (decimal degrees)

### Rate Limits

- **Anonymous users**: Maximum 1 request per 10 seconds
- **Authenticated users (OAuth2)**: Higher limits, typically 1 request per 5 seconds
- Exceeding limits results in HTTP 429 (Too Many Requests)

### Authentication

OpenSky supports OAuth2 authentication using client credentials:
1. Create an account at https://opensky-network.org
2. Generate OAuth2 credentials from your account settings
3. Download the `credentials.json` file
4. Use the client ID and secret for authenticated requests

## Response Format

### Successful Response (HTTP 200)

```json
{
  "time": 1234567890,
  "states": [
    [
      "abc123",           // [0]  icao24 - unique aircraft identifier
      "DLH123 ",          // [1]  callsign - flight number
      "Germany",          // [2]  origin_country
      1234567890,         // [3]  time_position - Unix timestamp
      1234567890,         // [4]  last_contact - Unix timestamp
      8.5622,             // [5]  longitude (decimal degrees)
      50.0379,            // [6]  latitude (decimal degrees)
      10058.4,            // [7]  baro_altitude (meters)
      false,              // [8]  on_ground (boolean)
      236.52,             // [9]  velocity (m/s)
      45.0,               // [10] true_track (degrees, 0=North)
      -3.25,              // [11] vertical_rate (m/s)
      null,               // [12] sensors (array of int)
      10363.2,            // [13] geo_altitude (meters)
      "1234",             // [14] squawk (transponder code)
      false,              // [15] spi (special position indicator)
      0                   // [16] position_source (0=ADS-B, 1=ASTERIX, 2=MLAT)
    ]
  ]
}
```

### Empty Response

```json
{
  "time": 1234567890,
  "states": null
}
```

### Error Responses

- **HTTP 400**: Invalid parameters
- **HTTP 401**: Authentication failed
- **HTTP 429**: Rate limit exceeded
- **HTTP 500**: Internal server error

## State Vector Fields Explained

| Index | Field Name | Type | Description |
|-------|------------|------|-------------|
| 0 | `icao24` | string | Unique ICAO 24-bit address (aircraft identifier) |
| 1 | `callsign` | string | Flight callsign (flight number), may be null |
| 2 | `origin_country` | string | Country of aircraft registration |
| 3 | `time_position` | int | Unix timestamp of position update |
| 4 | `last_contact` | int | Unix timestamp of last message |
| 5 | `longitude` | float | Longitude in decimal degrees, may be null |
| 6 | `latitude` | float | Latitude in decimal degrees, may be null |
| 7 | `baro_altitude` | float | Barometric altitude in meters, may be null |
| 8 | `on_ground` | boolean | True if aircraft is on ground |
| 9 | `velocity` | float | Speed over ground in m/s, may be null |
| 10 | `true_track` | float | Heading in degrees (0°=North), may be null |
| 11 | `vertical_rate` | float | Vertical speed in m/s, may be null |
| 12 | `sensors` | array | IDs of receivers that contributed data |
| 13 | `geo_altitude` | float | Geometric altitude in meters, may be null |
| 14 | `squawk` | string | Transponder code, may be null |
| 15 | `spi` | boolean | Special position indicator |
| 16 | `position_source` | int | 0=ADS-B, 1=ASTERIX, 2=MLAT |

## Data Collection in LARA

LARA's flight data collection works through the following process:

### 1. **Bounding Box Calculation**

The system calculates a geographic bounding box around your home location with the function located in `lara/utils/get_bounding_box`:

```python
from lara.utils import get_bounding_box

# Example: 50km radius around Frankfurt a. M.
latitude = 50.114
longitude = 8.679
radius_km = 50

# Calculate bounding box
lamin, lomin, lamax, lomax = get_bounding_box(latitude, longitude, radius_km)
```

### 2. **API Request**

LARA makes periodic requests to OpenSky with the bounding box:

```python
api_url = "https://opensky-network.org/api/states/all"
params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}
response = requests.get(api_url, params=params, timeout=10)
data = response.json()
```

### 3. **API Request with optional authentification**

The authentification credentials are commonly used with the following tooling, provided by `lara/tracking/auth` module.

```python
# Using LARA's authentication module
from lara.tracking.auth import OpenSkyAuth

auth = OpenSkyAuth(credentials_path="credentials.json")
response = auth.make_authenticated_request(api_url, params=params)
```

### 4. **Data Processing**

For each aircraft in the response:
- Extract position (latitude, longitude, altitude)
- Calculate distance from home using Haversine formula
- Filter by radius (remove aircraft outside tracking area)
- Store in SQLite database with timestamp

With the function `parse_state_vector` the output vector is parsed into a readable dictionary.

```python
from lara.utils import parse_state_vector

states = data["states"]
for state in states:
    state_data = parse_state_vector(state)
    print(state_data["icao24"])
```

### 5. **Database Storage**

Each flight is tracked with:
- **Flight record**: Unique flight session (ICAO24 + callsign)
- **Position updates**: Time-series of position, altitude, speed
- **Statistics**: Min/max altitude, closest approach, duration

### 6. **Continuous Collection**

LARA runs in a loop, respecting rate limits:
- Wait 10-15 seconds between requests (configurable)
- Handle errors gracefully (timeouts, rate limits)
- Update daily statistics
- Track flight sessions (same flight over time)

## Best Practices

### 1. Respect Rate Limits
- Wait at least 10 seconds between requests for anonymous access
- Use OAuth2 authentication for better limits

### 2. Use Bounding Boxes
- Reduce data volume by requesting only your area of interest
- Smaller areas = faster responses

### 3. Handle Errors Gracefully
- API can timeout or return errors
- Implement retry logic with exponential backoff

### 4. Validate Data
- Check for null values in position and altitude fields
- Some aircraft don't transmit all data

### 5. Cache Data
- Store historical data locally
- Avoid re-fetching the same information

## Resources

- **API Documentation**: https://openskynetwork.github.io/opensky-api/
- **OpenSky Network**: https://opensky-network.org/
- **ADS-B Explained**: https://en.wikipedia.org/wiki/Automatic_Dependent_Surveillance-Broadcast
- **LARA Project**: See README.md and documentation in `docu/` for complete system documentation