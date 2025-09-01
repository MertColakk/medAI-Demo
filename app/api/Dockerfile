FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN useradd -u 10001 -m appuser

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

WORKDIR /app
COPY . /app/api/
RUN chown -R appuser:appuser /app/api/

ENV MODEL_PATH=/app/api/models/weight.h5 \
    TF_NUM_INTRAOP_THREADS=2 \
    TF_NUM_INTEROP_THREADS=2

EXPOSE 8001

USER 10001

CMD ["python", "-m", "api.app"]