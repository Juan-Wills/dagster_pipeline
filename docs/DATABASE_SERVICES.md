# Database Services Documentation

## Overview
This Docker Compose setup includes three database services:
1. **PostgreSQL (Dagster)** - For Dagster's internal metadata
2. **PostgreSQL (Application)** - For application data
3. **MongoDB** - For document-based data storage

---

## PostgreSQL - Dagster (Internal)

This PostgreSQL instance is used by Dagster for storing run metadata, schedules, and other internal data.

### Connection Details
- **Host**: `postgres` (within Docker network) / `localhost` (from host machine)
- **Port**: `5432`
- **Database**: `dagster_pipeline`
- **Username**: `juan-wills`
- **Password**: `juan1234`

### Connection String
```
postgresql://juan-wills:juan1234@localhost:5432/dagster_pipeline
```

---

## PostgreSQL - Application

This PostgreSQL instance is for your application data.

### Connection Details
- **Host**: `postgresql` (within Docker network) / `localhost` (from host machine)
- **Port**: `5433` (mapped from internal 5432)
- **Database**: `appdb`
- **Username**: `appuser`
- **Password**: `apppassword`

### Connection String
```
# From host machine
postgresql://appuser:apppassword@localhost:5433/appdb

# From within Docker network
postgresql://appuser:apppassword@postgresql:5432/appdb
```

### Python Connection Example
```python
import psycopg2

# From host machine
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="appdb",
    user="appuser",
    password="apppassword"
)

# From within Docker container
conn = psycopg2.connect(
    host="postgresql",
    port=5432,
    database="appdb",
    user="appuser",
    password="apppassword"
)
```

---

## MongoDB

Document-oriented NoSQL database for flexible data storage.

### Connection Details
- **Host**: `mongodb` (within Docker network) / `localhost` (from host machine)
- **Port**: `27017`
- **Database**: `appdb`
- **Root Username**: `admin`
- **Root Password**: `mongopassword`

### Connection String
```
# From host machine
mongodb://admin:mongopassword@localhost:27017/appdb?authSource=admin

# From within Docker network
mongodb://admin:mongopassword@mongodb:27017/appdb?authSource=admin
```

### Python Connection Example
```python
from pymongo import MongoClient

# From host machine
client = MongoClient(
    host="localhost",
    port=27017,
    username="admin",
    password="mongopassword",
    authSource="admin"
)
db = client.appdb

# From within Docker container
client = MongoClient(
    host="mongodb",
    port=27017,
    username="admin",
    password="mongopassword",
    authSource="admin"
)
db = client.appdb
```

---

## Docker Commands

### Start all services
```bash
docker-compose up -d
```

### Start specific service
```bash
docker-compose up -d postgresql
docker-compose up -d mongodb
```

### Stop services
```bash
docker-compose down
```

### Stop services and remove volumes (WARNING: deletes all data)
```bash
docker-compose down -v
```

### View logs
```bash
docker-compose logs postgresql
docker-compose logs mongodb
```

### Check service status
```bash
docker-compose ps
```

---

## Database Management Tools

### PostgreSQL
You can use these tools to manage PostgreSQL:
- **psql** (command-line):
  ```bash
  docker exec -it postgresql_app psql -U appuser -d appdb
  ```
- **pgAdmin** (GUI): Connect using host `localhost`, port `5433`
- **DBeaver** (GUI): Universal database tool

### MongoDB
You can use these tools to manage MongoDB:
- **mongosh** (command-line):
  ```bash
  docker exec -it mongodb mongosh -u admin -p mongopassword --authenticationDatabase admin
  ```
- **MongoDB Compass** (GUI): Use connection string `mongodb://admin:mongopassword@localhost:27017/?authSource=admin`
- **Studio 3T** (GUI): Professional MongoDB GUI

---

## Data Persistence

All database data is persisted in Docker volumes:
- `postgres-data`: Dagster PostgreSQL data
- `postgresql-data`: Application PostgreSQL data
- `mongodb-data`: MongoDB data files
- `mongodb-config`: MongoDB configuration files

These volumes ensure your data persists even when containers are stopped or recreated.

---

## Security Notes

⚠️ **IMPORTANT**: The current passwords are for development only!

For production environments:
1. Change all passwords in the `.env` file to strong, unique values
2. Never commit the `.env` file to version control
3. Use secrets management tools (e.g., Docker Secrets, HashiCorp Vault)
4. Limit network exposure (consider not exposing ports publicly)
5. Enable SSL/TLS connections
6. Implement proper user roles and permissions

---

## Troubleshooting

### Connection Refused
- Ensure services are running: `docker-compose ps`
- Check logs: `docker-compose logs [service-name]`
- Verify ports aren't already in use: `netstat -tulpn | grep [port]`

### Container Won't Start
- Check logs: `docker-compose logs [service-name]`
- Verify environment variables in `.env` file
- Ensure no port conflicts with other services

### Data Not Persisting
- Verify volumes exist: `docker volume ls`
- Don't use `docker-compose down -v` unless you want to delete data
- Check volume mounts in docker-compose.yml

### Authentication Failed
- Double-check credentials in `.env` file
- Ensure you're using the correct port (5432 vs 5433 for PostgreSQL)
- For MongoDB, verify `authSource=admin` in connection string
