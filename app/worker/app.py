import os
from typing import Any, Dict, List
from PIL import Image, UnidentifiedImageError
from flask import Flask, request, jsonify
import numpy as np
from keras import models
import psycopg2, psycopg2.extras

# ---------- Model ----------
class Model:
    def __init__(self):
        model_path = os.getenv("MODEL_PATH", "/app/worker/models/weight.h5")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        self.model = models.load_model(model_path)
        self.classes = ["COVID-19", "NORMAL", "PNEUMONIA", "TUBERCULOSIS"]

    def _preprocess(self, image: Image.Image) -> np.ndarray:
        image = image.resize((224, 224))
        image = np.array(image, dtype=np.float32) / 255.0
        if image.ndim == 2:  # grayscale -> RGB
            image = np.stack([image] * 3, axis=-1)
        if image.shape[-1] == 4:  # RGBA -> RGB
            image = image[..., :3]
        image = np.expand_dims(image, axis=0)
        return image

    def predict(self, image: Image.Image) -> str:
        arr = self._preprocess(image)
        preds = self.model.predict(arr, verbose=0)
        idx = int(np.argmax(preds, axis=-1)[0])
        return self.classes[idx]


# ---------- Database ----------
class Database:
    """Minimal Postgres helper for JSONB logging + readiness."""
    def __init__(self):
        self.DB_NAME = os.getenv("DB", "xray")
        self.DB_HOST = os.getenv("DB_HOST", "postgres")
        self.DB_PORT = os.getenv("DB_PORT", "5432")
        self.DB_USER = os.getenv("DB_USER", "xray_user")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
        self.DSN = (
            f"dbname={self.DB_NAME} user={self.DB_USER} password={self.DB_PASSWORD} "
            f"host={self.DB_HOST} port={self.DB_PORT}"
        )
        self._allowed_tables = {"logs_user", "logs_error", "logs_access"}

    def connect(self, timeout: int = 3):
        return psycopg2.connect(dsn=self.DSN, connect_timeout=timeout)

    def insert_json(self, table: str, ip: str, payload: Dict[str, Any]) -> None:
        """Safe JSONB insert; restrict table names to known set."""
        if table not in self._allowed_tables:
            raise ValueError(f"invalid table: {table}")
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'INSERT INTO {table} (ip, payload) VALUES (%s, %s)',
                (ip, psycopg2.extras.Json(payload)),
            )
            conn.commit()

    def check_ready(self) -> bool:
        try:
            with self.connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return True
        except Exception:
            return False


# ---------- DTO ----------
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

# ---------- Service ----------
class Service:
    def __init__(self):
        self.model = Model()
        self.MAX_FILES = 16
        self.database = Database()

    def _client_ip(self, req) -> str:
        return req.headers.get("X-Forwarded-For", req.remote_addr or "")

    def predict(self, req):
        client_ip = self._client_ip(req)

        files: List = []
        if "images[]" in req.files:
            files = req.files.getlist("images[]")
        elif "image" in req.files:
            files = req.files.getlist("image")

        if not files:
            try:
                self.database.insert_json("logs_error", client_ip, {"reason": "no-file"})
            except Exception:
                pass
            return ErrorDTO(
                value="No file uploaded. Send as multipart/form-data with field name 'image' or 'images[]'.",
            )

        if len(files) > self.MAX_FILES:
            files = files[: self.MAX_FILES]

        results = []
        for f in files:
            fname = getattr(f, "filename", None)
            if not fname:
                results.append({"filename": None, "ok": False, "error": "empty-filename"})
                continue

            try:
                img = Image.open(f.stream).convert("RGB")
                pred = self.model.predict(img)

                results.append({"filename": fname, "ok": True, "prediction": pred})

                # Optional: user log
                try:
                    self.database.insert_json("logs_user", client_ip, {
                        "action": "predict",
                        "filename": fname,
                        "prediction": pred
                    })
                except Exception:
                    pass

            except UnidentifiedImageError:
                results.append({"filename": fname, "ok": False, "error": "invalid-image"})
                try:
                    self.database.insert_json("logs_error", client_ip, {
                        "where": "predict",
                        "filename": fname,
                        "error": "invalid-image"
                    })
                except Exception:
                    pass

            except Exception as e:
                results.append({"filename": fname, "ok": False, "error": str(e)})
                try:
                    self.database.insert_json("logs_error", client_ip, {
                        "where": "predict",
                        "filename": fname,
                        "error": str(e)
                    })
                except Exception:
                    pass

        # Access log (request metadata)
        try:
            self.database.insert_json("logs_access", client_ip, {
                "path": "/api/predict",
                "method": "POST",
                "files_count": len(files),
                "content_type": req.content_type,
            })
        except Exception:
            pass

        return SuccessDTO(value=results)

    def readyz(self):
        return SuccessDTO(value="ready")

    def livez(self):
        return SuccessDTO(value="alive")


# ---------- API ----------
app = Flask(__name__)
svc = Service()

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)