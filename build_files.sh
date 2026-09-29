#!/bin/bash
set -e

echo "===> STARTING VERCEL BUILD PROCESS <==="

# Determine python command
if command -v python3.12 &>/dev/null; then
    PY="python3.12"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    PY="python"
fi

echo "Using Python command: $PY ($($PY --version))"

# Install dependencies with --break-system-packages
$PY -m pip install -r requirements.txt --break-system-packages || $PY -m pip install -r requirements.txt

# Run database migrations
$PY manage.py migrate --noinput

# Seed cinema database with movies, theaters, showtimes, reviews & users
$PY manage.py seed_cinema_data || true

# Collect static files into staticfiles/
$PY manage.py collectstatic --noinput --clear

echo "===> VERCEL BUILD COMPLETED SUCCESSFULLY <==="
