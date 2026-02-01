# 🗄️ LARA Database Schema

**Complete reference for LARA's SQLite database structure**

---

## Overview

LARA uses a SQLite database to store flight tracking data, position updates, and daily statistics. The database is designed for efficient querying of both real-time data and historical analysis.

**Database Location**: Configured in `config.yaml` (default: `data/lara_flights.db`)

**Schema Version**: v1.0

---

## Table of Contents

1. [Tables](#tables)
   - [flights](#flights-table)
   - [positions](#positions-table)
   - [daily_stats](#daily_stats-table)
2. [Indexes](#indexes)
3. [Relationships](#relationships)
4. [Data Types](#data-types)
5. [Query Examples](#query-examples)
6. [Maintenance](#maintenance)

---

## Tables

### `flights` Table

Stores unique flight sessions. A flight session is defined as a continuous period where an aircraft with the same ICAO24 and callsign is tracked (with a timeout of 30 minutes between observations).

#### Schema

```sql
CREATE TABLE flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    icao24 TEXT NOT NULL,
    callsign TEXT,
    origin_country TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    min_distance_km REAL,
    max_altitude_m REAL,
    min_altitude_m REAL,
    avg_velocity_ms REAL,
    position_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-incrementing unique identifier |
| `icao24` | TEXT | NO | ICAO 24-bit aircraft address (e.g., "abc123") |
| `callsign` | TEXT | YES | Flight callsign (e.g., "DLH123") |
| `origin_country` | TEXT | YES | Country of aircraft registration |
| `first_seen` | TIMESTAMP | YES | First observation timestamp (ISO 8601 format) |
| `last_seen` | TIMESTAMP | YES | Last observation timestamp (ISO 8601 format) |
| `min_distance_km` | REAL | YES | Closest approach distance from home location (km) |
| `max_altitude_m` | REAL | YES | Maximum altitude observed (meters) |
| `min_altitude_m` | REAL | YES | Minimum altitude observed (meters) |
| `avg_velocity_ms` | REAL | YES | Average velocity (meters per second) |
| `position_count` | INTEGER | NO | Number of position updates for this flight |
| `created_at` | TIMESTAMP | NO | Database record creation timestamp |

#### Notes

- **Flight Session Logic**: Flights with the same `icao24` and `callsign` seen within 30 minutes are considered the same flight session
- **Callsign Format**: Typically 3-letter airline code + flight number (e.g., "DLH123", "AFR456")
- **Timestamps**: Stored in ISO 8601 format: `YYYY-MM-DD HH:MM:SS`
- **Statistics**: `min_distance_km`, `max_altitude_m`, `min_altitude_m` are computed from position updates

#### Example Data

```
id: 1
icao24: "abc123"
callsign: "DLH123"
origin_country: "Germany"
first_seen: "2025-01-31 14:23:15"
last_seen: "2025-01-31 14:45:32"
min_distance_km: 5.2
max_altitude_m: 10500.0
min_altitude_m: 9800.0
avg_velocity_ms: 250.0
position_count: 42
created_at: "2025-01-31 14:23:15"
```

---

### `positions` Table

Stores individual position updates for each flight, creating a complete trajectory history.

#### Schema

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    latitude REAL,
    longitude REAL,
    altitude_m REAL,
    geo_altitude_m REAL,
    velocity_ms REAL,
    heading REAL,
    vertical_rate_ms REAL,
    distance_from_home_km REAL,
    on_ground BOOLEAN,
    squawk TEXT,
    FOREIGN KEY (flight_id) REFERENCES flights(id) ON DELETE CASCADE
);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key, auto-incrementing unique identifier |
| `flight_id` | INTEGER | NO | Foreign key to `flights.id` |
| `timestamp` | TIMESTAMP | NO | Position observation timestamp (ISO 8601) |
| `latitude` | REAL | YES | Latitude in decimal degrees (-90 to 90) |
| `longitude` | REAL | YES | Longitude in decimal degrees (-180 to 180) |
| `altitude_m` | REAL | YES | Barometric altitude in meters |
| `geo_altitude_m` | REAL | YES | Geometric (GPS) altitude in meters |
| `velocity_ms` | REAL | YES | Ground speed in meters per second |
| `heading` | REAL | YES | True track/heading in degrees (0-360) |
| `vertical_rate_ms` | REAL | YES | Vertical rate in meters per second (+ = climbing) |
| `distance_from_home_km` | REAL | YES | Distance from home location in kilometers |
| `on_ground` | BOOLEAN | YES | True if aircraft is on ground |
| `squawk` | TEXT | YES | Transponder code (e.g., "1200", "7700") |

#### Notes

- **Position Frequency**: Typically updated every 10-15 seconds during collection
- **Altitude Types**: 
  - `altitude_m`: Barometric altitude (pressure-based, standard for aviation)
  - `geo_altitude_m`: GPS altitude (geometric height above sea level)
- **Heading**: 0° = North, 90° = East, 180° = South, 270° = West
- **Vertical Rate**: Positive = climbing, negative = descending, in meters/second
- **Cascade Delete**: Deleting a flight automatically deletes all associated positions

#### Example Data

```
id: 1234
flight_id: 1
timestamp: "2025-01-31 14:23:15"
latitude: 49.3508
longitude: 8.1364
altitude_m: 10200.0
geo_altitude_m: 10250.0
velocity_ms: 245.5
heading: 87.3
vertical_rate_ms: 2.5
distance_from_home_km: 5.2
on_ground: 0
squawk: "1200"
```

---

### `daily_stats` Table

Aggregated daily statistics for quick reporting and trend analysis.

#### Schema

```sql
CREATE TABLE daily_stats (
    date DATE PRIMARY KEY,
    total_flights INTEGER,
    total_positions INTEGER,
    avg_altitude_m REAL,
    min_distance_km REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `date` | DATE | NO | Date for statistics (YYYY-MM-DD) |
| `total_flights` | INTEGER | YES | Total flights observed this date |
| `total_positions` | INTEGER | YES | Total position updates this date |
| `avg_altitude_m` | REAL | YES | Average altitude across all positions (meters) |
| `min_distance_km` | REAL | YES | Closest approach this date (kilometers) |
| `updated_at` | TIMESTAMP | NO | Last update timestamp |

#### Notes

- **Update Trigger**: Updated automatically at midnight or when collector stops
- **Date Format**: Stored as `YYYY-MM-DD` (e.g., "2025-01-31")
- **Aggregation**: Computed from positions table grouped by date

#### Example Data

```
date: "2025-01-31"
total_flights: 145
total_positions: 6823
avg_altitude_m: 10234.5
min_distance_km: 3.2
updated_at: "2025-01-31 23:59:59"
```

---

## Indexes

Indexes are created to optimize common query patterns:

```sql
-- Flight lookups
CREATE INDEX idx_flights_icao24 ON flights(icao24);
CREATE INDEX idx_flights_callsign ON flights(callsign);
CREATE INDEX idx_flights_first_seen ON flights(first_seen);

-- Position queries
CREATE INDEX idx_positions_flight_id ON positions(flight_id);
CREATE INDEX idx_positions_timestamp ON positions(timestamp);
```

### Index Usage

| Index | Optimizes | Common Queries |
|-------|-----------|----------------|
| `idx_flights_icao24` | Aircraft lookups | Finding flights by aircraft |
| `idx_flights_callsign` | Callsign searches | Search by flight number |
| `idx_flights_first_seen` | Time-based queries | Recent flights, date ranges |
| `idx_positions_flight_id` | Position retrieval | Get all positions for a flight |
| `idx_positions_timestamp` | Temporal analysis | Time-series queries |

---

## Relationships

```
┌─────────────┐
│   flights   │
│             │
│ id (PK)     │───┐
│ icao24      │   │
│ callsign    │   │
│ ...         │   │
└─────────────┘   │
                  │
                  │ 1:N
                  │
                  │
┌─────────────┐   │
│  positions  │   │
│             │   │
│ id (PK)     │   │
│ flight_id   │───┘
│ timestamp   │
│ latitude    │
│ longitude   │
│ ...         │
└─────────────┘

┌─────────────┐
│ daily_stats │
│             │
│ date (PK)   │
│ ...         │
└─────────────┘
```

### Relationship Details

- **One-to-Many**: `flights` → `positions`
  - One flight has many position updates
  - Foreign key: `positions.flight_id` → `flights.id`
  - Cascade delete: Removing a flight deletes all positions

- **Independent**: `daily_stats`
  - Derived table, no foreign keys
  - Computed from flights and positions

---

## Data Types

### Coordinate Precision

- **Latitude/Longitude**: Stored as REAL with ~6 decimal places
  - Precision: ~0.11 meters at the equator
  - Range: Latitude [-90, 90], Longitude [-180, 180]

### Altitude Values

- **Meters**: Primary unit for all altitude values
- **Typical Range**: 0 to 15,000 meters (0 to ~49,000 feet)
- **NULL Handling**: Indicates no altitude data available

### Timestamps

- **Format**: ISO 8601: `YYYY-MM-DD HH:MM:SS`
- **Timezone**: UTC (recommended) or local time (configured)
- **SQLite Storage**: TEXT type with date/time functions

### Boolean Values

- **Storage**: INTEGER (0 = false, 1 = true)
- **Usage**: `on_ground` field

---

## Query Examples

### Find Recent Flights

```sql
SELECT 
    callsign, 
    icao24, 
    origin_country,
    first_seen,
    min_distance_km,
    position_count
FROM flights
WHERE first_seen >= datetime('now', '-24 hours')
ORDER BY first_seen DESC
LIMIT 20;
```

### Get Complete Flight Route

```sql
SELECT 
    p.timestamp,
    p.latitude,
    p.longitude,
    p.altitude_m,
    p.velocity_ms,
    p.heading
FROM positions p
WHERE p.flight_id = 123
ORDER BY p.timestamp;
```

### Top Airlines by Traffic

```sql
SELECT 
    SUBSTR(callsign, 1, 3) as airline_code,
    COUNT(*) as flight_count,
    AVG(min_distance_km) as avg_distance
FROM flights
WHERE callsign IS NOT NULL
GROUP BY airline_code
ORDER BY flight_count DESC
LIMIT 10;
```

### Hourly Traffic Distribution

```sql
SELECT 
    CAST(strftime('%H', first_seen) AS INTEGER) as hour,
    COUNT(*) as flight_count
FROM flights
GROUP BY hour
ORDER BY hour;
```

### Altitude Distribution

```sql
SELECT 
    CASE 
        WHEN altitude_m < 1000 THEN '0-1000m'
        WHEN altitude_m < 3000 THEN '1000-3000m'
        WHEN altitude_m < 6000 THEN '3000-6000m'
        WHEN altitude_m < 9000 THEN '6000-9000m'
        WHEN altitude_m < 12000 THEN '9000-12000m'
        ELSE '12000m+'
    END as altitude_range,
    COUNT(*) as count
FROM positions
WHERE altitude_m IS NOT NULL
GROUP BY altitude_range
ORDER BY MIN(altitude_m);
```

### Closest Approaches

```sql
SELECT 
    f.callsign,
    f.icao24,
    f.origin_country,
    f.min_distance_km,
    f.min_altitude_m,
    f.first_seen
FROM flights f
WHERE f.min_distance_km IS NOT NULL
ORDER BY f.min_distance_km ASC
LIMIT 10;
```

### Daily Statistics

```sql
SELECT 
    DATE(first_seen) as date,
    COUNT(*) as flights,
    AVG(min_distance_km) as avg_distance,
    MIN(min_distance_km) as closest_approach
FROM flights
WHERE first_seen >= date('now', '-7 days')
GROUP BY DATE(first_seen)
ORDER BY date DESC;
```

---

## Maintenance

### Database Size

- **Growth Rate**: ~1-5 MB per day (depends on traffic and update frequency)
- **Typical Size**: 50-500 MB for weeks/months of data
- **Position Data**: Primary contributor to database size

### Optimization

```sql
-- Analyze database for query optimization
ANALYZE;

-- Vacuum to reclaim space (run periodically)
VACUUM;

-- Rebuild indexes
REINDEX;
```

### Backup

```bash
# SQLite database backup
sqlite3 data/lara_flights.db ".backup data/lara_flights_backup.db"

# Or simple file copy
cp data/lara_flights.db data/lara_flights_backup.db
```

### Data Retention

Consider implementing data retention policies for large databases:

```sql
-- Delete positions older than 90 days
DELETE FROM positions 
WHERE timestamp < date('now', '-90 days');

-- Delete flights with no positions
DELETE FROM flights 
WHERE position_count = 0;

-- Update daily stats after cleanup
-- (Run via Python script)
```

---

## Schema Evolution

**Current Version**: v1.0

Future versions may include:
- Weather data integration
- Aircraft type/model information
- Noise level estimates
- Flight plan data
- Airport proximity tracking

Schema migrations will be handled through versioned update scripts.

---

## Technical Notes

### SQLite Configuration

Recommended SQLite pragmas for LARA:

```sql
PRAGMA journal_mode = WAL;      -- Write-Ahead Logging for better concurrency
PRAGMA synchronous = NORMAL;    -- Balance between safety and speed
PRAGMA foreign_keys = ON;       -- Enforce foreign key constraints
PRAGMA cache_size = -64000;     -- 64MB cache
```

### Performance Considerations

- **Batch Inserts**: Collector uses transactions for efficient bulk inserts
- **Index Strategy**: Indexes balance query speed vs. write performance
- **Cascade Deletes**: Enabled for data integrity
- **NULL Values**: Used judiciously to indicate missing data

### Data Integrity

- **Foreign Keys**: Enforced to maintain referential integrity
- **NOT NULL Constraints**: Applied to critical fields
- **Default Values**: Provided where appropriate
- **Validation**: Application-level validation before database writes