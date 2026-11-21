FROM python:3.11-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10

# Copy application code and dependencies
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Add db package to path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
