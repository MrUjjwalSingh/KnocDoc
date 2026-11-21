FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2, GeoAlchemy2)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and dependencies
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Add db package to path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
