#!/bin/bash
set -e

echo "🚀 Setting up KIND cluster for todo-app..."

# Create KIND cluster
echo "📦 Creating KIND cluster..."
kind create cluster --config k8s/local/kind-config.yaml

# Install NGINX Ingress Controller
echo "🌐 Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller to be ready
echo "⏳ Waiting for ingress controller..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

echo "✅ KIND cluster ready!"
echo "📝 Add '127.0.0.1 todo.local' to your /etc/hosts file"