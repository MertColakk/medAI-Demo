#!/bin/bash
minikube delete && minikube start --memory=3000 --addons=ingress,metrics-server --cni=cilium 
kubectl apply -f k8s/core/00-namespace.yaml && kubectl config set-context --current --namespace=xray-api 

# KYVERNO
kubectl create ns kyverno --dry-run=client -o yaml | kubectl apply -f -
helm repo add kyverno https://kyverno.github.io/kyverno
helm repo update
helm install kyverno kyverno/kyverno -n kyverno --set enablePolicyException=true

# Wait for all Kyverno controllers installed by the chart
kubectl wait --for=condition=available -n kyverno deploy/kyverno-admission-controller --timeout=180s
kubectl wait --for=condition=available -n kyverno deploy/kyverno-background-controller --timeout=180s
kubectl wait --for=condition=available -n kyverno deploy/kyverno-cleanup-controller --timeout=180s
kubectl wait --for=condition=available -n kyverno deploy/kyverno-reports-controller --timeout=180s

# BUILD
eval $(minikube docker-env) && docker build -t py-api:0.0.1 app/api/ 

# MANIFESTS
kubectl apply -f k8s/core && kubectl apply -f k8s/cluster 
kubectl apply -f k8s/database && kubectl apply -f k8s/api 
kubectl apply -f k8s/network