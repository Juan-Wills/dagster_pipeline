# Quick Start: PostgreSQL and MongoDB Services

This guide will help you get started with the new PostgreSQL and MongoDB services in your Dagster pipeline.

## 🚀 Getting Started

### 1. Install Required Dependencies

First, install the database client libraries:

```bash
# Install database dependencies
pip install psycopg2-binary pymongo sqlalchemy

# Or install all dependencies including databases
pip install -e ".[dagster,google-api,databases,dev]"
```

### 2. Start the Services

Start all Docker services (including PostgreSQL and MongoDB):

```bash
docker-compose up -d
```

To start only the database services:

```bash
docker-compose up -d postgresql mongodb
```

### 3. Verify Services are Running

Check that all services are healthy:

```bash
docker-compose ps
```

You should see:
- `postgresql_app` - Running on port 5433
- `mongodb` - Running on port 27017

### 4. Test Connections

#### Test PostgreSQL Connection

```bash
# From command line
docker exec -it postgresql_app psql -U appuser -d appdb

# Inside psql shell, run:
\dt  # List tables
\q   # Quit
```

#### Test MongoDB Connection

```bash
# From command line
docker exec -it mongodb mongosh -u admin -p mongopassword --authenticationDatabase admin

# Inside mongosh shell, run:
show dbs           # List databases
use appdb          # Switch to appdb
show collections   # List collections
exit               # Quit
```

## 📊 Using the Resources in Dagster

### Add Resources to Your Definitions

Update your `dagster_pipeline/definitions.py`:

```python
from dagster import Definitions
from dagster_pipeline.resources import (
    GoogleDriveResource,
    PostgreSQLResource,
    MongoDBResource
)
from dagster_pipeline.resources.duckdb_connection import DuckDBResource

# Import your assets
from dagster_pipeline.assets import (
    google_drive_etl,
    database_examples
)

# Define resources
defs = Definitions(
    assets=[
        # Your existing assets
        google_drive_etl,
        database_examples,
    ],
    resources={
        "google_drive": GoogleDriveResource(
            credentials_path="auth/credentials.json",
            token_path="auth/token.json"
        ),
        "duckdb": DuckDBResource(
            database_path="data/duckdb/prueba.duckdb"
        ),
        "postgresql": PostgreSQLResource(
            host="localhost",  # or "postgresql" if running inside Docker
            port=5433,
            database="appdb",
            user="appuser",
            password="apppassword"
        ),
        "mongodb": MongoDBResource(
            host="localhost",  # or "mongodb" if running inside Docker
            port=27017,
            database="appdb",
            username="admin",
            password="mongopassword",
            auth_source="admin"
        ),
    }
)
```

### Example Asset Using PostgreSQL

```python
from dagster import asset, AssetExecutionContext
from dagster_pipeline.resources.postgresql_resource import PostgreSQLResource
import pandas as pd

@asset
def my_postgres_asset(
    context: AssetExecutionContext,
    postgresql: PostgreSQLResource
) -> dict:
    """Store data in PostgreSQL."""
    
    # Create sample data
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    # Create table from DataFrame
    postgresql.create_table_from_dataframe(
        df=df,
        table_name='users',
        if_exists='replace'
    )
    
    # Query the data
    results = postgresql.execute_query("SELECT * FROM users")
    context.log.info(f"Inserted {len(results)} rows")
    
    return {"rows_inserted": len(results)}
```

### Example Asset Using MongoDB

```python
from dagster import asset, AssetExecutionContext
from dagster_pipeline.resources.mongodb_resource import MongoDBResource
import pandas as pd

@asset
def my_mongodb_asset(
    context: AssetExecutionContext,
    mongodb: MongoDBResource
) -> dict:
    """Store data in MongoDB."""
    
    # Create sample data
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
    
    # Insert DataFrame as documents
    doc_count = mongodb.insert_dataframe(
        collection_name='users',
        df=df,
        replace=True
    )
    
    # Query the data
    users = mongodb.find_many('users', filter={'age': {'$gte': 30}})
    context.log.info(f"Found {len(users)} users age 30 or older")
    
    return {"documents_inserted": doc_count}
```

## 🔧 Configuration

### Environment Variables

All database credentials are stored in `.env`:

```bash
# Application PostgreSQL
APP_POSTGRES_USER=appuser
APP_POSTGRES_PASSWORD=apppassword
APP_POSTGRES_DB=appdb

# MongoDB
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=mongopassword
MONGO_DB=appdb
```

⚠️ **IMPORTANT**: Change these passwords in production!

### Connection from Docker Containers

If your Dagster code runs inside Docker containers, use these hostnames:
- PostgreSQL: `postgresql` (not `localhost`)
- MongoDB: `mongodb` (not `localhost`)

### Connection from Host Machine

If running Dagster locally (not in Docker), use:
- PostgreSQL: `localhost:5433`
- MongoDB: `localhost:27017`

## 📝 Common Tasks

### View Logs

```bash
# PostgreSQL logs
docker-compose logs -f postgresql

# MongoDB logs
docker-compose logs -f mongodb
```

### Restart Services

```bash
# Restart specific service
docker-compose restart postgresql
docker-compose restart mongodb

# Restart all services
docker-compose restart
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ DELETES ALL DATA)
docker-compose down -v
```

### Backup Data

#### PostgreSQL Backup

```bash
# Backup database
docker exec postgresql_app pg_dump -U appuser appdb > backup.sql

# Restore database
docker exec -i postgresql_app psql -U appuser appdb < backup.sql
```

#### MongoDB Backup

```bash
# Backup database
docker exec mongodb mongodump --username admin --password mongopassword --authenticationDatabase admin --db appdb --out /tmp/backup

# Copy backup from container
docker cp mongodb:/tmp/backup ./mongodb_backup

# Restore database
docker exec mongodb mongorestore --username admin --password mongopassword --authenticationDatabase admin --db appdb /tmp/backup/appdb
```

## 🐛 Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
sudo netstat -tulpn | grep :5433
sudo netstat -tulpn | grep :27017

# Change the port in docker-compose.yml
# For PostgreSQL: "5434:5432"
# For MongoDB: "27018:27017"
```

### Connection Refused

1. Check services are running: `docker-compose ps`
2. Check logs: `docker-compose logs postgresql mongodb`
3. Verify .env file has correct credentials
4. Ensure you're using correct hostname (localhost vs service name)

### Permission Denied

```bash
# Fix volume permissions
sudo chown -R $USER:$USER data/
```

## 📚 Additional Resources

- [DATABASE_SERVICES.md](./DATABASE_SERVICES.md) - Detailed database documentation
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MongoDB Documentation](https://www.mongodb.com/docs/)
- [Dagster Resources Guide](https://docs.dagster.io/concepts/resources)

## 🎯 Next Steps

1. ✅ Start the services: `docker-compose up -d`
2. ✅ Install dependencies: `pip install psycopg2-binary pymongo sqlalchemy`
3. ✅ Add resources to your definitions
4. ✅ Create assets that use the databases
5. ✅ Run your pipeline: `dagster dev`

Happy coding! 🚀
