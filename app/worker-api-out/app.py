import os
import requests
from flask import Flask, request as flask_request, jsonify

DEFAULT_BASE = "http://python-svc.xray-api.svc.cluster.local:8001"  

class Service:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or os.getenv("INTERNAL_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()  

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def predict(self, flask_req):
        try:
            files = []
            if "images[]" in flask_req.files:
                for f in flask_req.files.getlist("images[]"):
                    files.append(("images[]", (f.filename, f.stream, f.mimetype)))
            elif "image" in flask_req.files:
                for f in flask_req.files.getlist("image"):
                    files.append(("image", (f.filename, f.stream, f.mimetype)))

            if not files:
                return jsonify({"ok": False, "error": "no-file",
                                "hint": "Send multipart/form-data with field 'image' or 'images[]'."}), 400

            r = self.session.post(
                url=self._url("/api/predict"),
                files=files,            
                timeout=self.timeout,
            )
            return (r.text, r.status_code, list(r.headers.items()))
        except requests.RequestException as e:
            return jsonify({"error": "upstream_error", "detail": str(e)}), 502
        
    def readyz(self):
        try:
            r = self.session.get(self._url("/api/readyz"), timeout=self.timeout)
            return (r.text, r.status_code, list(r.headers.items()))
        except requests.RequestException as e:
            return jsonify({"status": "not_ready", "detail": str(e)}), 503

    def livez(self):
        try:
            r = self.session.get(self._url("/api/livez"), timeout=self.timeout)
            return (r.text, r.status_code, list(r.headers.items()))
        except requests.RequestException as e:
            return jsonify({"status": "not_live", "detail": str(e)}), 502


app = Flask(__name__)
svc = Service(base_url=DEFAULT_BASE)

@app.route("/readyz", methods=["GET"])
def readyz():
    return svc.readyz()

@app.route("/livez", methods=["GET"])
def livez():
    return svc.livez()

@app.route("/predict", methods=["POST"])
def predict():    
    return svc.predict(flask_request)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
