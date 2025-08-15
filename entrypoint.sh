#!/bin/bash

# echo "Running migrations..."
# uv run python manage.py migrate --noinput


# Collect static files if in production
if [ "$DEBUG" == "False" ]; then
  echo "Collecting static files..."
  uv run python manage.py collectstatic --noinput
fi

# Run the command passed to the entrypoint
exec "$@"