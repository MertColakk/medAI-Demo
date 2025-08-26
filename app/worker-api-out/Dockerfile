FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

# put the code under /app so PYTHONPATH works cleanly
WORKDIR /app
COPY . /app/worker/

EXPOSE 8000

# Use WSGI workers (sync or gthread). Point at module:app
CMD ["python", "-m", "worker.app"]