# JARVIS Application Dockerfile
FROM python:3.12-alpine AS runtime

LABEL maintainer="maintainers@example.com"
LABEL description="JARVIS Personal AI Operating System core platform"

WORKDIR /app

# Install runtime dependencies only
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source, migrations, and alembic config
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini ./

# Create a secure non-root user and set permissions
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Default command: run the JARVIS API server
CMD ["python3", "-m", "jarvis"]
