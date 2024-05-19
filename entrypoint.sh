#!/bin/sh

# Create necessary directories
mkdir -p /app/migrations

# Initialize the database
python /app/init_db.py


# Run the Flask application
exec gunicorn --bind 0.0.0.0:5000 app:app
