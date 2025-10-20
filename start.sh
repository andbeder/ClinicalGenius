#!/bin/bash
# Start the Synthetic Claims Data Generator

echo "Starting Synthetic Claims Data Generator..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Activate virtual environment and run Flask
source venv/bin/activate
python app.py
