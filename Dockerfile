# Track B1 sync-serving image; intentionally excludes GeoLife raw files and artifacts.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GEOLIFE_PRIVATE_DEMO=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir . \
    && useradd --system --uid 10001 --create-home geolife

USER geolife
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

# Avoid logging path parameters (e.g. legacy v1 user IDs) in EC2/CloudWatch access logs.
CMD ["uvicorn", "geolife.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
