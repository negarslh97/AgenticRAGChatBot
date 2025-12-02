# Multi-stage build for SallyBot on Hugging Face Spaces
# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY sally-frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy frontend source
COPY sally-frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Python Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY sally-backend/release/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY sally-backend/ ./sally-backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/build ./sally-frontend/build

# Create necessary directories
RUN mkdir -p logs uploads

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/sally-backend

# Expose port (Hugging Face Spaces uses PORT env var, default is 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; import os; port = os.getenv('PORT', '7860'); requests.get(f'http://localhost:{port}/api/system/health')" || exit 1

# Run the application
CMD ["/app/start.sh"]

