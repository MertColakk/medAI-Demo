#!/bin/bash
minikube delete && minikube start --memory=3000 --addons=ingress,metrics-server --cni=cilium 
kubectl apply -f k8s/core/00-namespace.yaml && kubectl config set-context --current --namespace=xray-api 
eval $(minikube docker-env) && docker build -t py-api:0.0.1 app/worker/ && kubectl apply -f k8s/core && kubectl apply -f k8s/database && kubectl apply -f k8s/api && kubectl apply -f k8s/network 