"""
Entry point for Hugging Face Spaces deployment.
This file is required by Hugging Face Spaces to run the application.

Note: In Docker deployment, the app runs via start.sh script.
This file is kept for compatibility with Hugging Face Spaces UI.
"""

import os
import sys

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'sally-backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Change to backend directory for relative imports
original_cwd = os.getcwd()
try:
    os.chdir(backend_path)
    # Import the FastAPI app from main.py
    from main import app
finally:
    os.chdir(original_cwd)

# Hugging Face Spaces expects the app to be available as 'app'
__all__ = ['app']

