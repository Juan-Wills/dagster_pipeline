#!/bin/bash
set -e

# Start dagster daemon in background
dagster-daemon run -w /dagster_pipeline/pipeline/workspace.yaml &

# Start webserver in foreground (keeps container alive)
exec dagster-webserver -h 0.0.0.0 -p 3000 -w /dagster_pipeline/pipeline/workspace.yaml