# 🛩️ LARA - Local Air Route Analysis

Track, analyze, and visualize aircraft flights over your location using real-time ADS-B data.

```
 ___       ________  ________  ________     
|\  \     |\   __  \|\   __  \|\   __  \    
\ \  \    \ \  \|\  \ \  \|\  \ \  \|\  \   
 \ \  \    \ \   __  \ \   _  _\ \   __  \  
  \ \  \____\ \  \ \  \ \  \\  \\ \  \ \  \ 
   \ \_______\ \__\ \__\ \__\\ _\\ \__\ \__\
    \|_______|\|__|\|__|\|__|\|__|\|__|\|__|
```

---

## ✨ What is LARA?

LARA transforms ADS-B flight data from the [OpenSky Network](https://opensky-network.org/) into actionable insights about air traffic patterns over your location. Whether you're curious about the planes flying overhead, researching air traffic patterns, or analyzing aviation noise, LARA provides the tools you need.

**Key Features:**
- 📡 **Real-time flight tracking** with automatic data collection
- 🗺️ **Interactive visualizations** showing flight paths and corridors
- 📊 **Statistical analysis** of traffic patterns, airlines, and altitudes
- 🔍 **Pattern detection** for recurring routes and schedules
- 💾 **Local database** storing complete flight history

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/dan1elw/LARA.git
cd LARA
pip install -r requirements.txt
```

### Configure Your Location

Creat your own config giving an example in `docu/example/config.yaml`:

```yaml
location:
  latitude: 52.516257
  longitude: 13.377525
  name: "Berlin, Germany"

tracking:
  radius_km: 35
  update_interval_seconds: 15
```

### Start Collecting Data

```bash
python scripts/collect.py --config "path-to-your-config"
```

That's it! LARA will start tracking flights in your area and storing data in a local SQLite database.

---

## 📊 What Can You Do?

### 2. **Analyze Traffic Patterns**

```bash
python scripts/analyze.py --config "path-to-your-config"
```

Comprehensive analysis including:
- Recurring flight detection with corridor clustering
- Temporal patterns (hourly/daily trends)
- Airline statistics
- Route variations

### 3. **Visualize Flight Patterns**

```bash
python scripts/visualize.py --dashboard
```

Generates a complete visualization dashboard with:
- Flight corridor maps showing common routes
- Traffic density heatmaps
- Recent flight paths
- Altitude analysis

---

## 🎯 Use Cases

- **Aviation Enthusiasts**: Track and identify aircraft in your area
- **Researchers**: Analyze air traffic patterns and trends
- **Noise Analysis**: Identify low-altitude flight corridors
- **Flight Spotting**: Log and visualize interesting flights
- **Data Science**: Practice with real-world geospatial data

---

## 🔧 How It Works

1. **Data Collection**: LARA queries the OpenSky Network API every 15 seconds for flights within your specified radius
2. **Storage**: Flight positions and metadata are stored in a SQLite database
3. **Analysis**: Advanced algorithms detect flight corridors, patterns, and statistical trends
4. **Visualization**: Interactive maps and dashboards make the data accessible and insightful

---

## 🌟 Advanced Features

### OAuth2 Authentication
For higher rate limits and better performance we would recommend:

1. Create an account at [OpenSky Network](https://opensky-network.org/)
2. Download your `credentials.json` from your account settings
3. Update `config.yaml` with the credentials path

### Pattern Detection
LARA automatically identifies:
- Recurring flight routes
- Regular schedules
- Flight corridors (linear paths with multiple flights)
- Temporal patterns

### Extensible Architecture
- Modular design for easy customization
- Skills system for advanced document creation
- Well-documented codebase for contributions

---

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- [Configuration Options](docu/lara_configuration.md)
- [Usage Examples](docu/lara_example.md)
- [Database Schema](docu/lara_database_schema.md)
- [OpenSky API Documentation](docu/lara_opensky_api.md)

---

## 🛠️ Requirements

- **Python 3.8+**
- **Internet connection** for OpenSky Network API access
- **~50MB disk space** for database (grows with collected data)

**Core Dependencies:**
- `requests` - API communication
- `folium` - Interactive map generation
- `pyyaml` - Configuration management
- `pytest` - Testing framework

check out the `requirements.txt` file for more details.

---

## Disclaimer

This project was developed using AI as a coding partner, combining human direction with AI-assisted implementation.

LARA is under active development. Features and APIs may change. Feedback and contributions are greatly appreciated!

---

<p align="center">
  made with ❤️ for aviation enthusiasts and data scientists
</p>