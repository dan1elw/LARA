# LARA - Local Air Route Analysis

🛩️ Track, analyze, and visualize aircraft flights over your location using ADS-B data from OpenSky Network.

## Features

- **Real-time flight tracking** - Monitor aircraft in your area
- **Comprehensive database** - Store complete flight paths and metadata
- **Route analysis** - Identify common flight corridors and patterns
- **Statistical insights** - Analyze traffic by time, altitude, airline, and more
- **Interactive queries** - Explore your data with built-in reader tools

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/LARA.git
cd LARA
pip install -r requirements.txt
```

### Configuration

Edit `config.yaml` to set your location:

```yaml
location:
  latitude: 49.3508
  longitude: 8.1364
  name: "Neustadt an der Weinstraße"
  
tracking:
  radius_km: 50
  update_interval_seconds: 10
```

### Usage

**Start collecting data:**
```bash
python scripts/collect.py
```

**Read and analyze data:**
```bash
python scripts/read.py
```

## Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [Database Schema](docs/database_schema.md)
- [API Reference](docs/api_reference.md)

## Requirements

- Python 3.8+
- Internet connection
- Free OpenSky Network access (no API key required)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Acknowledgments

- [OpenSky Network](https://opensky-network.org/) for providing free ADS-B data
- Data collected from the OpenSky Network, https://opensky-network.org
