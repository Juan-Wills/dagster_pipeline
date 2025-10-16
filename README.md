# Dagster Pipeline

A production-ready Dagster ETL pipeline for processing CSV files from Google Drive using Docker.

## 🏗️ Project Structure

```
dagster_pipeline/
├── config/                      # Configuration files
│   ├── dagster.yaml            # Dagster instance config
│   ├── workspace.yaml          # Workspace definitions
│   └── __init__.py             # Settings and constants
│
├── dagster_pipeline/           # Main package
│   ├── assets/                 # Data assets
│   ├── resources/              # External resources (Google Drive, DB)
│   ├── jobs/                   # Job definitions
│   ├── sensors/                # Event sensors
│   ├── schedules/              # Scheduled runs
│   └── definitions.py          # Central Dagster definitions
│
├── data/                       # Data storage
│   ├── raw/                    # Downloaded raw data
│   ├── processed/              # Processed data
│   └── temp/                   # Temporary files
│
├── auth/                       # Authentication credentials
│   ├── credentials.json        # Google API credentials
│   └── token.json             # OAuth token
│
├── scripts/                    # Utility scripts
│   ├── setup_check.py         # Setup verification
│   └── quickstart.py          # Quick start guide
│
├── tests/                      # Test files
│   ├── conftest.py            # Pytest configuration
│   └── test_*.py              # Test modules
│
├── docker/                     # Docker configuration
│   ├── codespace.Dockerfile   # User code container
│   └── dagster_services.Dockerfile  # Dagster services
│
├── docs/                       # Documentation
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── QUICKSTART_GUIDE.md
│   └── SENSOR_SETUP.md
│
├── docker-compose.yml          # Docker orchestration
├── pyproject.toml             # Python dependencies
├── setup.py                   # Package setup
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Google Cloud account with Drive API enabled
- `uv` package manager (optional, for local development)

### 1. Setup Google Drive Credentials

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API
3. Create OAuth 2.0 credentials
4. Download and save as `auth/credentials.json`

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Start the Pipeline

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Access Dagster UI

Open your browser to: http://localhost:3000

## 📊 Features

- **Google Drive Integration**: Automatically download and process CSV files
- **Sensors**: Detect new files and trigger processing
- **Docker-based**: Fully containerized for easy deployment
- **PostgreSQL Storage**: Persistent run history and metadata
- **Modular Design**: Easy to extend with new assets and resources

## 🔧 Development

### Run Setup Check

```bash
python scripts/setup_check.py
```

### Local Development (without Docker)

```bash
# Install dependencies
uv sync --group dagster --group google-api

# Run Dagster dev server
dagster dev -f dagster_pipeline/definitions.py
```

### Run Tests

```bash
pytest tests/
```

## 📝 Configuration

All configuration is centralized in `config/__init__.py`:

- Project paths
- Data directories
- Authentication paths

## 🔐 Authentication

The first time you run the pipeline, it will:
1. Open a browser for Google OAuth
2. Request Drive API permissions
3. Save the token to `auth/token.json`

## 📚 Documentation

- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)
- [Quick Start Guide](docs/QUICKSTART_GUIDE.md)
- [Sensor Setup](docs/SENSOR_SETUP.md)

## 🛠️ Architecture

### Services

- **dagster-webserver**: Web UI (port 3000)
- **dagster-daemon**: Background scheduler and sensor runner
- **codespace**: User code server (port 4000)
- **postgres**: Metadata and run storage (port 5432)

### Data Flow

1. Sensor detects new CSV in Google Drive `raw_data` folder
2. Asset downloads file to `data/raw/`
3. Pandas processes the data (clean, transform)
4. Processed file saved to `data/processed/`
5. File uploaded to Google Drive `processed_data` folder

## 📦 Package Management

The project uses `uv` for fast dependency management:

```bash
# Add a new dependency
uv add <package-name>

# Update dependencies
uv sync

# Lock dependencies
uv lock
```

## 🐛 Troubleshooting

### Container Issues

```bash
# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Check Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs codespace
```

### Reset Database

```bash
docker compose down -v
docker compose up -d
```

## 📄 License

MIT License

## 👤 Author

Juan Wills

---

For more details, see the [documentation](docs/).
