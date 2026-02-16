#!/bin/sh
set -e

echo "Applying database migrations..."
python scripts/apply_migrations.py
echo "Migrations done. Starting application..."
exec "$@"
