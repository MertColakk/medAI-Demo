#!/usr/bin/env bash
set -euo pipefail

# ---- Configurable bits ----
XRAY_NS="xray-api"
XRAY_CRD_NAMES=("xrayapps.medai.mertcolakk.io")
KYVERNO_NS="kyverno"
KYVERNO_RELEASE="kyverno"
KYVERNO_CHART="kyverno/kyverno"
HELM_TIMEOUT="5m"

install() {
  echo "=> Installation started"

  # ---- Fresh minikube ----
  minikube delete || true
  minikube start --memory=3000 --addons=ingress,metrics-server --cni=cilium

  # ---- Namespaces ----
  kubectl create namespace "$XRAY_NS" --dry-run=client -o yaml | kubectl apply -f -
  kubectl config set-context --current --namespace="$XRAY_NS"

  # ---- Bootstrap admin SA (before admission policies kick in) ----
  echo "=> Creating bootstrap-admin ServiceAccount with cluster-admin"
  kubectl create namespace kube-system --dry-run=client -o yaml | kubectl apply -f - >/dev/null 2>&1 || true
  kubectl -n kube-system create sa bootstrap-admin --dry-run=client -o yaml | kubectl apply -f -
  kubectl create clusterrolebinding bootstrap-admin \
    --clusterrole=cluster-admin \
    --serviceaccount=kube-system:bootstrap-admin 2>/dev/null || true

  # We will impersonate this SA for privileged CREATE/UPDATE/DELETE later
  IMPERSONATE="--as=system:serviceaccount:kube-system:bootstrap-admin"

  # ---- Kyverno (Helm, HA & hardened) ----
  echo "=> Kyverno installing!"
  kubectl create ns "$KYVERNO_NS" --dry-run=client -o yaml | kubectl apply -f -
  helm repo add kyverno https://kyverno.github.io/kyverno
  helm repo update

  helm upgrade --install "$KYVERNO_RELEASE" "$KYVERNO_CHART" -n "$KYVERNO_NS" \
    --set enablePolicyException=true \
    --set replicaCount=2 \
    --set podDisruptionBudget.minAvailable=1 \
    --set securityContext.runAsNonRoot=true \
    --set containerSecurityContext.allowPrivilegeEscalation=false \
    --set containerSecurityContext.readOnlyRootFilesystem=true \
    --set resources.requests.cpu=200m \
    --set resources.requests.memory=256Mi \
    --set resources.limits.cpu=1 \
    --set resources.limits.memory=512Mi \
    --wait --timeout "$HELM_TIMEOUT"

  # ---- Wait Kyverno deployments ----
  echo "=> Waiting kyverno controllers to be available"
  kubectl -n "$KYVERNO_NS" wait --for=condition=available deploy/kyverno-admission-controller --timeout=180s
  kubectl -n "$KYVERNO_NS" wait --for=condition=available deploy/kyverno-background-controller --timeout=180s
  kubectl -n "$KYVERNO_NS" wait --for=condition=available deploy/kyverno-cleanup-controller --timeout=180s
  kubectl -n "$KYVERNO_NS" wait --for=condition=available deploy/kyverno-reports-controller --timeout=180s

  # ---- Wait CNI & Ingress readiness (reduce race) ----
  echo "=> Waiting Cilium & Ingress to be ready"
  kubectl -n kube-system wait --for=condition=Ready pod -l k8s-app=cilium --timeout=180s || true
  if kubectl get ns ingress-nginx >/dev/null 2>&1; then
    kubectl -n ingress-nginx wait --for=condition=Available deploy -l app.kubernetes.io/name=ingress-nginx --timeout=180s || true
  fi

  # ---- Build local images into minikube docker ----
  echo "=> Building images"
  eval "$(minikube docker-env)"
  docker buildx build -t py-api:0.0.1 app/api/ --load
  docker buildx build -t xray-operator:0.0.1 app/op/ --load

  # ---- Apply manifests (order & waits) ----
  echo "=> Applying manifests"
  kubectl apply -f k8s/00-core.yaml
  kubectl apply -f k8s/01-kyverno.yaml
  #kubectl apply -f k8s/02-network.yaml
  kubectl apply -f k8s/03-db.yaml

  kubectl apply -f k8s/04-operator-crd.yaml
  for crd in "${XRAY_CRD_NAMES[@]}"; do
    echo "=> Waiting CRD $crd to be Established"
    kubectl wait --for=condition=Established "crd/${crd}" --timeout=180s
  done

  # Operators and others
  kubectl apply -f k8s/05-operator.yaml
  kubectl apply -f k8s/06-security.yaml

  # ---- Make webhooks fail-closed (all entries, dynamic discovery) ----
  echo "=> Converting Kyverno webhooks to fail-closed"
  # ValidatingWebhookConfigurations (starts with kyverno-*)
  mapfile -t VCFG < <(kubectl get validatingwebhookconfigurations.admissionregistration.k8s.io -o json \
    | jq -r '.items[] | select(.metadata.name|test("^kyverno-")) | .metadata.name')
  for cfg in "${VCFG[@]:-}"; do
    [ -z "$cfg" ] && continue
    count=$(kubectl get validatingwebhookconfiguration "$cfg" -o json | jq '.webhooks|length')
    if [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -gt 0 ]; then
      patch='['
      for ((i=0; i<count; i++)); do
        patch+='{"op":"replace","path":"/webhooks/'"$i"'/failurePolicy","value":"Fail"},'
      done
      patch="${patch%,}]"
      kubectl patch validatingwebhookconfiguration "$cfg" --type='json' -p="$patch" $IMPERSONATE || true
    fi
  done

  # MutatingWebhookConfigurations (starts with kyverno-*)
  mapfile -t MCFG < <(kubectl get mutatingwebhookconfigurations.admissionregistration.k8s.io -o json \
    | jq -r '.items[] | select(.metadata.name|test("^kyverno-")) | .metadata.name')
  for cfg in "${MCFG[@]:-}"; do
    [ -z "$cfg" ] && continue
    count=$(kubectl get mutatingwebhookconfiguration "$cfg" -o json | jq '.webhooks|length')
    if [[ "$count" =~ ^[0-9]+$ ]] && [ "$count" -gt 0 ]; then
      patch='['
      for ((i=0; i<count; i++)); do
        patch+='{"op":"replace","path":"/webhooks/'"$i"'/failurePolicy","value":"Fail"},'
      done
      patch="${patch%,}]"
      kubectl patch mutatingwebhookconfiguration "$cfg" --type='json' -p="$patch" $IMPERSONATE || true
    fi
  done

  # ---- RBAC: delete cluster-admin bindings safely ----
  echo "=> Ensuring break-glass cluster-admin binding and pruning unwanted ones"

  # Give break-glass into current context users (as SA to pass admission policy)
  CURRENT_CTX="$(kubectl config current-context)"
  CURRENT_USER="$(kubectl config view -o jsonpath='{.contexts[?(@.name=="'"$CURRENT_CTX"'")].context.user}')"
  if [ -n "$CURRENT_USER" ]; then
    kubectl create clusterrolebinding break-glass-admin \
      --clusterrole=cluster-admin --user="$CURRENT_USER" $IMPERSONATE 2>/dev/null || true
  else
    echo "WARN: Could not resolve current kubectl user; skipping break-glass binding creation."
  fi

  # WHITE LIST
  WHITELIST_REGEX='^(break-glass-admin|bootstrap-admin|kubeadm:cluster-admin|minikube.*|xray-operator-.*|xray-api-.*)$'

  mapfile -t CRBS < <(kubectl get clusterrolebindings -o json \
    | jq -r '.items[] | select(.roleRef.kind=="ClusterRole" and .roleRef.name=="cluster-admin") | .metadata.name')
  for b in "${CRBS[@]:-}"; do
    [[ "$b" =~ $WHITELIST_REGEX ]] && { echo "  keep: $b"; continue; }
    echo "  delete: $b"
    kubectl delete clusterrolebinding "$b" $IMPERSONATE || true
  done

  echo "=> Verifying permissions"
  kubectl auth can-i update validatingwebhookconfigurations $IMPERSONATE
  kubectl auth can-i delete clusterrolebindings $IMPERSONATE

  echo "=> Installation completed"
}

run() {
  #minikube service -n xray-api xray-api-svc --url
  kubectl -n xray-api port-forward svc/xray-api-svc 8081:8081
}

database() {
  kubectl -n xray-api exec -it postgres-0 -- bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

usage() {
  cat <<'EOF'
Usage: ./manage.sh <command>

Commands:
  --install         Start minikube, install Kyverno, build images, apply manifests
  --run             Print the service URL for python-api-svc in the xray-api namespace
  --database | db   Open a psql shell inside postgres-0
  --help            Show this help

Notes:
  - The database command uses POSTGRES_USER and POSTGRES_DB from the pod's env.
Examples:
  ./manage.sh --install
  ./manage.sh --run
  ./manage.sh --db
EOF
}

main() {
  cmd="${1:-help}"; shift || true
  case "$cmd" in
    --install|-i|install)   install "$@";;
    --run|-r|run)           run "$@";;
    --database|--db|database) database "$@";;
    --help|-h|help)         usage;;
    *) echo "Unknown command: $cmd"; echo; usage; exit 1;;
  esac
}

main "$@"
