#!/bin/bash
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

# Install dependencies
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt

# Run migrations (creates tables for serverless instance)
$PY manage.py migrate --noinput

# Collect static files into staticfiles/
$PY manage.py collectstatic --noinput --clear

echo "===> VERCEL BUILD COMPLETED SUCCESSFULLY <==="
