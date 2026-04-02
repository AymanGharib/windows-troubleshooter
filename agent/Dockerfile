# Use the Python 3.12 slim base image for standalone deployment
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ---- Install system dependencies ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ---- Install Python dependencies ----
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# --- Copy Application Code ---
COPY app/ app/
COPY .env.example .env

# --- Run the standalone server ---
CMD ["python", "-m", "app"]
