import kopf
import kubernetes as k8s
from kubernetes import config

try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

apps = k8s.client.AppsV1Api()
core = k8s.client.CoreV1Api()
autoscale = k8s.client.AutoscalingV2Api()

class Operator:
    def __init__(self, namespace, name, spec) -> None:
        self.ns = namespace
        self.name = name
        self.spec = spec or {}

        # --- Parse ---
        self.enable_pdb    = bool(self.spec.get("enablePDB"))
        self.MIN_AVAILABLE = int(self.spec.get("minAvailable"))

        self.enable_hpa   = bool(self.spec.get("enableHPA"))
        self.replicas     = int(self.spec.get("replicas"))
        self.MIN_REPLICAS = int(self.spec.get("minReplicas"))
        self.MAX_REPLICAS = int(self.spec.get("maxReplicas"))
        self.cpu_target   = int(self.spec.get("cpuTarget"))

        self.auto_token   = bool(self.spec.get("automountServiceAccountToken"))

        self.port         = int(self.spec.get("port"))
        self.service_type = str(self.spec.get("serviceType"))
        self.service_name = str(self.spec.get("serviceName"))

        self.image        = str(self.spec.get("image"))
        self.image_policy = str(self.spec.get("imagePullPolicy"))
        self.ready        = str(self.spec.get("readinessPath"))
        self.live         = str(self.spec.get("livenessPath"))
        self.add_app_armor = bool(self.spec.get("addAppArmorAnno"))
        self.config_map   = str(self.spec.get("configMapRef"))
        self.secret       = str(self.spec.get("secretRef"))
        self.seccomp_type = str(self.spec.get("seccompType"))

    # ---------- Manifests ----------
    def build_service_account(self) -> dict:
        return {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {"name": f"{self.name}-sa", "namespace": self.ns},
            "automountServiceAccountToken": self.auto_token,
        }

    def build_service(self) -> dict:
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

    def build_deployment(self) -> dict:
        pod_meta = {"labels": {"app": self.name}}
        if self.add_app_armor:
            pod_meta.setdefault("annotations", {})[
                f"container.apparmor.security.beta.kubernetes.io/{self.name}"
            ] = "runtime/default"

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

    def build_hpa(self) -> dict:
        if not self.enable_hpa:
            return None
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

    def build_pdb(self) -> dict:
        if not self.enable_pdb:
            return None
        return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": {"name": f"{self.name}-pdb", "namespace": self.ns},
            "spec": {"minAvailable": self.MIN_AVAILABLE,
                     "selector": {"matchLabels": {"app": self.name}}},
        }

# ---------- Upsert helpers ----------
def upsert(owner, obj) -> None:
    if obj is None:
        return
    kind = obj["kind"]
    name = obj["metadata"]["name"]
    ns   = obj["metadata"]["namespace"]

    kopf.adopt(obj, owner=owner)  

    try:
        if kind == "Deployment":
            apps.read_namespaced_deployment(name, ns)
            apps.patch_namespaced_deployment(name, ns, obj)
        elif kind == "Service":
            core.read_namespaced_service(name, ns)
            core.patch_namespaced_service(name, ns, obj)
        elif kind == "ServiceAccount":
            core.read_namespaced_service_account(name, ns)
            core.patch_namespaced_service_account(name, ns, obj)
        elif kind == "HorizontalPodAutoscaler":
            autoscale.read_namespaced_horizontal_pod_autoscaler(name, ns)
            autoscale.patch_namespaced_horizontal_pod_autoscaler(name, ns, obj)
        elif kind == "PodDisruptionBudget":
            k8s.client.PolicyV1Api().read_namespaced_pod_disruption_budget(name, ns)
            k8s.client.PolicyV1Api().patch_namespaced_pod_disruption_budget(name, ns, obj)
    except k8s.client.exceptions.ApiException as e:
        if e.status == 404:
            if kind == "Deployment":
                apps.create_namespaced_deployment(ns, obj)
            elif kind == "Service":
                core.create_namespaced_service(ns, obj)
            elif kind == "ServiceAccount":
                core.create_namespaced_service_account(ns, obj)
            elif kind == "HorizontalPodAutoscaler":
                autoscale.create_namespaced_horizontal_pod_autoscaler(ns, obj)
            elif kind == "PodDisruptionBudget":
                k8s.client.PolicyV1Api().create_namespaced_pod_disruption_budget(ns, obj)
        else:
            raise

# ---------- Kopf event handlers ----------
@kopf.on.create('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
@kopf.on.update('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
def reconcile(spec, name, namespace, body, **_) -> dict:
    op = Operator(namespace, name, spec)

    sa  = op.build_service_account()
    svc = op.build_service()
    dep = op.build_deployment()
    hpa = op.build_hpa()
    pdb = op.build_pdb()

    # SA -> Service -> Deployment -> HPA/PDB
    for obj in (sa, svc, dep, hpa, pdb):
        upsert(body, obj)

    d = apps.read_namespaced_deployment(name, namespace)
    ready = d.status.ready_replicas or 0
    return {"readyReplicas": ready}

@kopf.on.delete('medai.mertcolakk.io', 'v1alpha1', 'xrayapps')
def cleanup(**_) -> None:
    pass