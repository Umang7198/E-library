#!/bin/bash

# Initialize the SQLite database
flask db upgrade

# Run the Gunicorn server
exec gunicorn --bind 0.0.0.0:5000 app:app
