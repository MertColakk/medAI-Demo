# app.py
import os
import json
import time
import uuid
import logging
import signal
import threading
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True 

from flask import Flask, request, jsonify, g
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import RequestEntityTooLarge

import numpy as np
from keras import models

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from psycopg2 import sql

# =========================
# Config / Settings
# =========================
class Settings:
    MODEL_PATH: str = os.getenv("MODEL_PATH", "/app/worker/models/weight.h5")
    CLASSES: List[str] = os.getenv(
        "MODEL_CLASSES",
        "COVID-19,NORMAL,PNEUMONIA,TUBERCULOSIS"
    ).split(",")

    MAX_FILES: int = int(os.getenv("MAX_FILES", "16"))
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_MB", "20")) * 1024 * 1024
    ALLOWED_MIME: Tuple[str, ...] = tuple(
        os.getenv("ALLOWED_MIME", "image/jpeg,image/png,image/webp,image/heif,image/heic").split(",")
    )

    # DB
    DB_NAME: str = os.getenv("DB", "xray")
    DB_HOST: str = os.getenv("DB_HOST", "postgres-hl")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "xray_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "12345")
    DB_APP_NAME: str = os.getenv("DB_APP_NAME", "python-api")
    DB_MIN_CONN: int = int(os.getenv("DB_MIN_CONN", "1"))
    DB_MAX_CONN: int = int(os.getenv("DB_MAX_CONN", "5"))
    DB_CONNECT_TIMEOUT: int = int(os.getenv("DB_CONNECT_TIMEOUT", "3"))
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "audit")

    LOG_TABLE_USER: str = os.getenv("LOGS_USER_TABLE", "logs_user")
    LOG_TABLE_ERROR: str = os.getenv("LOGS_ERROR_TABLE", "logs_error")
    LOG_TABLE_ACCESS: str = os.getenv("LOGS_ACCESS_TABLE", "logs_access")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    READY_CHECK_SQL: str = os.getenv("READY_CHECK_SQL", "SELECT 1")

SET = Settings()

# =========================
# Logging (JSON structured)
# =========================
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extras") and isinstance(record.extras, dict):
            payload.update(record.extras)
        return json.dumps(payload, ensure_ascii=False)

def get_logger(name="app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(SET.LOG_LEVEL)
        logger.propagate = False
    return logger

log = get_logger("api")

# =========================
# Model (thread-safe load)
# =========================
class Model:
    _lock = threading.Lock()
    _loaded = False

    def __init__(self):
        with Model._lock:
            if not Model._loaded:
                if not os.path.exists(SET.MODEL_PATH):
                    raise FileNotFoundError(f"Model file not found at {SET.MODEL_PATH}")
                self.model = models.load_model(SET.MODEL_PATH)
                Model._loaded = True
            else:
                self.model = models.load_model(SET.MODEL_PATH)
        self.classes = SET.CLASSES

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        image = image.convert("RGB").resize((224, 224))
        arr = np.array(image, dtype=np.float32) / 255.0
        arr = np.expand_dims(arr, axis=0)
        return arr

    def predict(self, image: Image.Image) -> str:
        arr = self._preprocess(image)
        preds = self.model.predict(arr, verbose=0)
        idx = int(np.argmax(preds, axis=-1)[0])
        return self.classes[idx]

# =========================
# Database (pool + safe SQL)
# =========================
class Database:
    """Postgres helper with connection pool and JSONB logging."""
    def __init__(self):
        dsn = (
            f"dbname={SET.DB_NAME} user={SET.DB_USER} password={SET.DB_PASSWORD} "
            f"host={SET.DB_HOST} port={SET.DB_PORT} application_name={SET.DB_APP_NAME}"
        )
        self.pool = SimpleConnectionPool(
            SET.DB_MIN_CONN, SET.DB_MAX_CONN,
            dsn=dsn, connect_timeout=SET.DB_CONNECT_TIMEOUT,
            keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5
        )
        self.allowed_tables = {
            (SET.DB_SCHEMA, SET.LOG_TABLE_USER),
            (SET.DB_SCHEMA, SET.LOG_TABLE_ERROR),
            (SET.DB_SCHEMA, SET.LOG_TABLE_ACCESS),
        }

    def _get_conn(self):
        return self.pool.getconn()

    def _put_conn(self, conn):
        if conn:
            self.pool.putconn(conn)

    def insert_json(self, table_pair: Tuple[str, str], ip: Optional[str], payload: Dict[str, Any]) -> None:
        """table_pair = (schema, table). Uses safe identifier quoting."""
        if table_pair not in self.allowed_tables:
            raise ValueError(f"invalid table: {table_pair}")
        conn = self._get_conn()
        try:
            with conn, conn.cursor() as cur:
                query = sql.SQL("INSERT INTO {}.{} (ip, payload) VALUES (%s, %s)").format(
                    sql.Identifier(table_pair[0]), sql.Identifier(table_pair[1])
                )
                cur.execute(query, (ip, psycopg2.extras.Json(payload)))
        finally:
            self._put_conn(conn)

    def check_ready(self) -> bool:
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(SET.READY_CHECK_SQL)
                cur.fetchone()
            return True
        except Exception as e:
            log.warning("ready_check_failed", extra={"extras": {"error": str(e)}})
            return False
        finally:
            self._put_conn(conn)

    def close(self):
        try:
            self.pool.closeall()
        except Exception:
            pass

# =========================
# DTOs
# =========================
class ErrorDTO:
    def __init__(self, value, status: int = 400):
        self.ok = False
        self.key = "error"
        self.value = value
        self.status = status

class SuccessDTO:
    def __init__(self, value, status: int = 200):
        self.ok = True
        self.key = "response"
        self.value = value
        self.status = status

# =========================
# Service
# =========================
class Service:
    def __init__(self):
        self.model = Model()
        self.database = Database()
        self.max_files = SET.MAX_FILES

    @staticmethod
    def client_ip(req) -> str:
        xff = req.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return req.remote_addr or ""

    def predict(self, req):
        client_ip = self.client_ip(req)

        if req.mimetype not in ("multipart/form-data", "application/octet-stream"):
            return ErrorDTO(value="Unsupported Content-Type. Use multipart/form-data.", status=415)

        files: List = []
        if "images[]" in req.files:
            files = req.files.getlist("images[]")
        elif "image" in req.files:
            files = req.files.getlist("image")

        if not files:
            self._safe_log(("audit", SET.LOG_TABLE_ERROR), client_ip, {"reason": "no-file"})
            return ErrorDTO(
                value="No file uploaded. Send as multipart/form-data with field name 'image' or 'images[]'.",
                status=400
            )

        if len(files) > self.max_files:
            files = files[: self.max_files]

        results = []
        for f in files:
            fname = getattr(f, "filename", None)
            if not fname:
                results.append({"filename": None, "ok": False, "error": "empty-filename"})
                continue

            if hasattr(f, "mimetype") and f.mimetype and SET.ALLOWED_MIME and f.mimetype.lower() not in SET.ALLOWED_MIME:
                results.append({"filename": fname, "ok": False, "error": "unsupported-mime"})
                self._safe_log(("audit", SET.LOG_TABLE_ERROR), client_ip, {
                    "where": "predict", "filename": fname, "error": "unsupported-mime", "mimetype": f.mimetype
                })
                continue

            try:
                img = Image.open(f.stream)  
                pred = self.model.predict(img)

                results.append({"filename": fname, "ok": True, "prediction": pred})

                self._safe_log(("audit", SET.LOG_TABLE_USER), client_ip, {
                    "action": "predict", "filename": fname, "prediction": pred
                })

            except UnidentifiedImageError:
                results.append({"filename": fname, "ok": False, "error": "invalid-image"})
                self._safe_log(("audit", SET.LOG_TABLE_ERROR), client_ip, {
                    "where": "predict", "filename": fname, "error": "invalid-image"
                })

            except Exception as e:
                results.append({"filename": fname, "ok": False, "error": "internal-error"})
                self._safe_log(("audit", SET.LOG_TABLE_ERROR), client_ip, {
                    "where": "predict", "filename": fname, "error": str(e)
                })
                log.exception("predict_failed", extra={"extras": {"filename": fname}})

        self._safe_log(("audit", SET.LOG_TABLE_ACCESS), client_ip, {
            "path": "/api/predict",
            "method": "POST",
            "files_count": len(files),
            "content_type": req.content_type,
        })

        return SuccessDTO(value=results)

    def readyz(self):
        db_ok = self.database.check_ready()
        model_ok = os.path.exists(SET.MODEL_PATH)
        status = 200 if (db_ok and model_ok) else 503
        return SuccessDTO(value={"db": db_ok, "model": model_ok}, status=status)

    def livez(self):
        return SuccessDTO(value="alive", status=200)

    def _safe_log(self, table_pair: Tuple[str, str], ip: Optional[str], payload: Dict[str, Any]) -> None:
        try:
            self.database.insert_json(table_pair, ip, payload)
        except Exception as e:
            log.warning("log_insert_failed", extra={"extras": {"table": ".".join(table_pair), "error": str(e)}})

# =========================
# Flask App
# =========================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)  
app.config["MAX_CONTENT_LENGTH"] = SET.MAX_CONTENT_LENGTH

svc = Service()

# =========================
# Request ID & Timing Middleware
# =========================
@app.before_request
def _before():
    g.req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    g.t0 = time.perf_counter()

@app.after_request
def _after(resp):
    dur_ms = int((time.perf_counter() - g.get("t0", time.perf_counter())) * 1000)
    resp.headers["X-Request-ID"] = g.get("req_id", "")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    try:
        log.info("access", extra={"extras": {
            "rid": g.get("req_id"),
            "path": request.path,
            "method": request.method,
            "status": resp.status_code,
            "duration_ms": dur_ms,
            "ip": Service.client_ip(request),
        }})
    except Exception:
        pass
    return resp

# =========================
# Error Handlers
# =========================
@app.errorhandler(RequestEntityTooLarge)
def _handle_413(e):
    dto = ErrorDTO(value="Payload too large", status=413)
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

@app.errorhandler(404)
def _handle_404(e):
    dto = ErrorDTO(value="Not found", status=404)
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

@app.errorhandler(Exception)
def _handle_500(e):
    log.exception("unhandled_exception", extra={"extras": {"path": request.path}})
    dto = ErrorDTO(value="Internal server error", status=500)
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

# =========================
# Endpoints
# =========================
@app.route("/api/readyz", methods=["GET"])
def readyz():
    dto = svc.readyz()
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

@app.route("/api/livez", methods=["GET"])
def livez():
    dto = svc.livez()
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

@app.route("/api/predict", methods=["POST"])
def predict():
    dto = svc.predict(request)
    return jsonify({"ok": dto.ok, dto.key: dto.value}), dto.status

def _graceful_shutdown(*_):
    try:
        svc.database.close()
    finally:
        os._exit(0)

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)