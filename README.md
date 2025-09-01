## DESCRIPTION
### KUBERNETES OBJECTS WHICH IS USED
-   Namespace
-   ConfigMap
-   Secrets
-   HorizontalPodAutoscaler
-   ResourceQuota (Namespace level resource management) 
-   LimitRange (Container level resource management)
-   Service
-   Job
-   Deployment
-   StatefulSet
-   ServiceAccount
-   PodDisruptionBudget
-   RBAC
-   CustomResourceDefinition
-   PolicyException

### TECHNOLOGIES OF APPLICATION
    -   PostgreSQL
    -   Python
    -   Kyverno
    -   Docker
    -   Kubernetes

### PYTHON LIBRARIES WHICH IS USED
    -   Tensorflow / Keras
    -   Pillow
    -   Flask / Flask-SQLAlchemy
    -   psycopg2
    -   kopf
    -   kubernetes

## ABOUT SYSTEM
### NAMES OF KUBERNETES OBJECTS
-   ##### KUBERNETES CORE
        -   Namespaces: xray-api
        -   ResourceQuota: python-api-rq
        -   LimitRange: python-api-lr
-   ##### DATABASE (**PostgreSQL**)
        -   ConfigMap: db-config
        -   Secrets: db-secrets
        -   Service: postgres-hl
        -   StatefulSet: postgres
        -   Job ConfigMap: db-init-sql
        -   Job: db-init
-   ##### API OPERATOR (**Kopf**)
        -   CustomResourceDefinition: XrayApp
        -   ServiceAccount: xray-operator
        -   Role: xray-operator-role
        -   RoleBinding: xray-operator-rb
        -   Deployment: xray-operator
        -   PolicyException: allow-no-apparmor-in-xray
    -   ###### API (**Python**)
            -   Service: python-api-svc
            -   ServiceAccount: python-api-sa
            -   Deployment: python-api
            -   HorizontalPodAutoscaler: python-api-hpa 
            -   PodDisruptionBudget: python-api-pdb
-   ##### NETWORK
        -   NetworkPolicy: default-deny-all
        -   NetworkPolicy: allow-dns
        -   NetworkPolicy: allow-api-public-ingress
        -   NetworkPolicy: allow-api-egress-to-db
        -   NetworkPolicy: allow-db-ingress
        -   NetworkPolicy: allow-dbinit-egress-to-db
-   ##### CLUSTER POLICY (**KYVERNO**)
        -   ClusterPolicy: enforce-pod-security-restricted
            -   require-seccomp
            -   require-container-security
        -   ClusterPolicy: sa-automount-disabled
            -   pod-sa-automount
        -   ClusterPolicy: disallow-latest-tag
            -   no-latest

### THE USED ADDONS IN KUBERNETES
    -   metrics-server -> for HPA
    -   ingress -> for HTTP access
    -   cilium -> for NetworkPolicy enforcement

## OPERATORS
    -   PostgreSQL Operator
    -   Image Classification API Operator

## SECURITY
### POD SECURITY STANDARDS
-   #### Namespace Level
    -   Containers are working as "non-root" user.
    -   No "privileged" containers. 
    -   "HostPath" volumes must be forbidden. 
    -   "AppArmor" must be applied. -> Kuburnetes "default"
    -   "Seccomp" profile must not be set to uncofined (***Kubernetes applies auto***)

### MANIFESTS OF KUBERNETES (in "core" folder)
-   **Created a namespace**
    -   A namespace is created for workload isolation.
-   **Determined resource quota and limit range**
    -   Limit ranges are defined for each container, and resource quotas are specified for the system.

### MANIFESTS OF DATABASE (in "database" folder)
-  **Database Configs**
    -   Non-sensitive data such as database host and database name are stored here.
-   **Database Sensitive Data**
    -   Sensitive data such as database user and password are stored here.
-   **Database StatefulSet**
    -   A StatefulSet is used because the database requires a persistent volume for storing data.
-   **Database Headless Service**
    -   Provides DNS records for each database Pod and ensures correct routing between them.
-   **Database Init Job**
    -   Runs initialization SQL scripts (like creating tables) when the database starts.

### MANIFESTS OF OPERATOR (in "operator" folder)
-   **Operator CRD**
    -   Defines a Custom Resource that extends the Kubernetes API with new object types managed by the operator.
-   **Operator Service Account**
    -   Provides an identity for the operator pods to interact with the Kubernetes API.
-   **Operator Role**
    -   Defines the permissions (rules) the operator needs to manage resources.
-   **Operator RoleBinding**
    -   Binds the Service Account to the Role, granting the operator the required permissions.
-   **Operator Deployment**
    -   Runs the operator as a Deployment inside the cluster, ensuring it is available and can reconcile custom resources.
    #### MANIFESTS OF API (in "app/op/operator/main.py")
    -   **API Service Account**
        -   Provides an identity for the API pods to securely interact with Kubernetes resources (if needed).
    -   **API Service**
        -   Exposes the API application on a specific port. Typically uses ClusterIP for internal access, or NodePort/LoadBalancer if external access is required.
    -   **API Deployment**
        -   Defines how the API application pods are created, managed, and updated (including mounting ConfigMaps and Secrets for configuration and database access).
    -   **API HPA**
        -   Automatically scales the number of API pods based on CPU/memory usage or custom metrics.
    -   **API PDB**
        -   Ensures a minimum number of API pods remain available during voluntary disruptions.

### MANIFESTS OF NETWORK (in "network" folder)
-   **Default Deny All Network Policy**
    -   All traffic is denied by default.
-   **Allow DNS Network Policy**
    -   Allows DNS resolution.
-   **Allow Requests to API Endpoint Network Policy**
    -   Allows inbound traffic to the API endpoint.
-   **Allow Requests to Postgres from API Network Policy**
    -   Allows the API to connect to Postgres for saving data.
-   **Allow Requests to API and Database Init Job from Postgres Network Policy**
    -   Allows communication between Postgres, the API, and the DB Init Job.
-   **Allow Requests to Postgres from DB Init Job Network Policy**
    -   Allows the DB Init Job to connect to Postgres for creating the database and initializing tables.

### MANIFESTS OF CLUSTER (in "cluster" folder)
-   **Pod Restriction Cluster Policy**
    -   All Pods must use seccompProfile. Each container must run as non-root, use readOnlyRootFilesystem, have privilege escalation disabled, and drop all Linux capabilities.
-   **Pod Service Account AutoMount Cluster Policy**
    -   Pods must not automatically mount ServiceAccount tokens unless explicitly required.
-   **Image Will Not Work If It Has Latest Tag Cluster Policy**
    -   Images using the latest tag are disallowed to prevent non-deterministic deployments.

## INSTALL & RUN
```bash
# Give execution permit into scripts (only for 1 time)
chmod +x install.sh start.sh database.sh

# Start installation
./install.sh

# Start service (local)
./start.sh

# Access into database (Optional)
./database.sh
```

## CODE REVIEW
### 1- AI MODEL STRUCTURE
```python
model = Sequential([
    Input(shape=(28, 28, 1)),

    Conv2D(64, (3, 3)),
    BatchNormalization(),
    ReLU(),
    Conv2D(64, (3, 3)),
    BatchNormalization(),
    ReLU(),
    MaxPool2D((2, 2)),

    Conv2D(128, (3, 3)),
    BatchNormalization(),
    ReLU(),
    Conv2D(128, (3, 3)),
    BatchNormalization(),
    ReLU(),
    MaxPool2D((2, 2)),

    Flatten(),

    Dense(128, activation="relu"),
    Dropout(0.2),
    Dense(self.dataset.num_classes, activation="softmax")
])

model.compile(
    optimizer=Adam(learning_rate=1e-3),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

callbacks = [
    EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
    ModelCheckpoint(filepath=os.path.join(self.save_path, "best_model.keras"), monitor="val_loss", save_best_only=True),
    ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5)        
]
```
### 2 - IMAGE CLASSIFIER API
#### 2.1 - Settings 
```python
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
```
#### 2.2 - AI Model
```python
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
```
#### 2.3 - Database
```python
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
```
#### 2.4 - Service
```python
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
```
#### 2.5 - Endpoints
```python
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
```
### 3 - API OPERATOR
#### 3.1 - Creating Manifests from Operator
```python
# Build service account
return {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {"name": f"{self.name}-sa", "namespace": self.ns},
            "automountServiceAccountToken": self.auto_token,
        }
# Build service
return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": f"{self.name}-svc", "namespace": self.ns, "labels": {"app": self.name}},
            "spec": {
                "type": self.service_type,
                "selector": {"app": self.name},
                "ports": [
                    {"name": self.service_name, "port": self.port, "targetPort": self.port}
                ],
            },
        }
# Build deployment
return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": self.name, "namespace": self.ns, "labels": {"app": self.name}},
            "spec": {
                "replicas": self.replicas,
                "selector": {"matchLabels": {"app": self.name}},
                "template": {
                    "metadata": pod_meta,
                    "spec": {
                        "securityContext": {"seccompProfile": {"type": self.seccomp_type}},
                        "serviceAccountName": f"{self.name}-sa",
                        "automountServiceAccountToken": self.auto_token,
                        "containers": [{
                            "name": self.name,
                            "image": self.image,
                            "imagePullPolicy": self.image_policy,
                            "ports": [{"containerPort": self.port, "name": self.service_name}],
                            "envFrom": [
                                {"configMapRef": {"name": self.config_map}},
                                {"secretRef": {"name": self.secret}},
                            ],
                            "readinessProbe": {
                                "httpGet": {"path": self.ready, "port": self.port},
                                "initialDelaySeconds": 5, "periodSeconds": 10,
                            },
                            "livenessProbe": {
                                "httpGet": {"path": self.live, "port": self.port},
                                "initialDelaySeconds": 10, "periodSeconds": 20,
                            },
                            "resources": {
                                "requests": {"cpu": "300m", "memory": "384Mi"},
                                "limits":   {"cpu": "1",    "memory": "768Mi"},
                            },
                            "securityContext": {
                                "runAsNonRoot": True,
                                "runAsUser": 10001, "runAsGroup": 10001,
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]},
                            },
                            "volumeMounts": [{"name": "tmp", "mountPath": "/tmp"}],
                        }],
                        "volumes": [{"name": "tmp", "emptyDir": {}}],
                    },
                },
            },
        }
# Build HPA
return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": f"{self.name}-hpa", "namespace": self.ns},
            "spec": {
                "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": self.name},
                "minReplicas": self.MIN_REPLICAS,
                "maxReplicas": self.MAX_REPLICAS,
                "metrics": [{
                    "type": "Resource",
                    "resource": {"name": "cpu",
                                 "target": {"type": "Utilization", "averageUtilization": self.cpu_target}},
                }],
            },
        }
# Build PDB
return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {"name": f"{self.name}-pdb", "namespace": self.ns},
            "spec": {"minAvailable": self.MIN_AVAILABLE,
                     "selector": {"matchLabels": {"app": self.name}}},
        }
```
#### 3.2 - Event Handler in workflow: SA -> SVC -> Deployment -> HPA/PDB
```python
@kopf.on.create('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
@kopf.on.update('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
def reconcile(spec, name, namespace, body, **_) -> dict:
    op = Operator(namespace, name, spec)

    sa  = op.build_service_account()
    svc = op.build_service()
    dep = op.build_deployment()
    hpa = op.build_hpa()
    pdb = op.build_pdb()

    for obj in (sa, svc, dep, hpa, pdb):
        upsert(body, obj)

    d = apps.read_namespaced_deployment(name, namespace)
    ready = d.status.ready_replicas or 0
    return {"readyReplicas": ready}
```
#### 3.3 - On delete (Clean up is auto no need to implement!)
```python
@kopf.on.delete('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
def cleanup(**_) -> None:
    pass
```

