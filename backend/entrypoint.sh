#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head || echo "Migrations failed or no new migrations"
echo "Starting application..."

exec "$@"
