# Multi-stage build for Astraeus Apertura
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create requirements file without heavy optional deps for base image
RUN pip install --no-cache-dir numpy scipy matplotlib pandas loguru tqdm pyyaml requests pydantic psutil

# Development stage - includes all dependencies
FROM base as development

# Install all requirements including dev tools
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install package in development mode
RUN pip install -e .

CMD ["python", "-m", "astraeus.cli"]

# Production stage - minimal dependencies
FROM base as production

# Install only core production requirements
COPY requirements.txt .
RUN grep -E "numpy|scipy|matplotlib|pandas|loguru|tqdm|pyyaml|requests|pydantic|psutil|plotly|dash|anthropic|openai|notion-client" requirements.txt > requirements-prod.txt && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy only necessary application code
COPY astraeus/ /app/astraeus/
COPY setup.py README.md ./

# Install package
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN useradd -m -u 1000 astraeus && \
    chown -R astraeus:astraeus /app

USER astraeus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import astraeus; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "astraeus"]

# API/Dashboard stage
FROM production as dashboard

EXPOSE 8050

CMD ["python", "-c", "from astraeus.visualization import create_dashboard; create_dashboard().run(host='0.0.0.0')"]

# Worker stage for job processing
FROM production as worker

ENV WORKER_THREADS=4

CMD ["python", "-m", "astraeus.scheduling.worker"]
