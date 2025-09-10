FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN useradd -u 10002 -m appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential && rm -rf /var/lib/apt/lists/*

COPY operator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY operator/ /app/
RUN chown -R appuser:appuser /app

USER 10002

ENTRYPOINT ["kopf", "run", "--standalone", "/app/main.py"]