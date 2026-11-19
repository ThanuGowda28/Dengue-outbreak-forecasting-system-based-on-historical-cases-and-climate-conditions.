FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/backend/requirements.txt
COPY backend /app/backend
RUN mkdir -p /app/backend/logs /app/backend/instance/uploads && useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app/backend
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '5000') + '/api/health', timeout=3)" || exit 1
CMD ["sh", "-c", "gunicorn --config backend/gunicorn.conf.py backend.run:app"]
