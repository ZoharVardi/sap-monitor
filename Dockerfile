# Dockerfile
FROM python:3.11-slim

# Install system deps (curl just for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement list inline (simple)
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests prometheus_client

# Copy your app code
COPY monitor_app.py /app/monitor_app.py

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "monitor_app:monitor_app", "--host", "0.0.0.0", "--port", "8000"]
