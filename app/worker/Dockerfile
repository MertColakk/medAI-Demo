FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

WORKDIR /app
COPY . /app/worker/

ENV MODEL_PATH=/app/worker/models/weight.h5 \
    TF_NUM_INTRAOP_THREADS=2 \
    TF_NUM_INTEROP_THREADS=2

EXPOSE 8001

# worker/app.py modülünü çalıştır
CMD ["python", "-m", "worker.app"]