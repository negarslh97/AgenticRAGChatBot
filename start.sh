#!/bin/bash
# Startup script for Hugging Face Spaces

# Get port from environment variable (Hugging Face Spaces provides this)
PORT=${PORT:-7860}

# Change to backend directory
cd /app/sally-backend

# Run the application
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT

