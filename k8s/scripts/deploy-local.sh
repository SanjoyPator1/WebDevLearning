#!/bin/bash
set -e

echo "🚀 Deploying todo-app to KIND..."

# Apply all manifests
echo "📝 Creating namespace..."
kubectl apply -f k8s/base/namespace.yaml

echo "🗄️  Deploying database..."
kubectl apply -f k8s/base/database/

echo "🔧 Deploying backend..."
kubectl apply -f k8s/base/backend/

echo "🎨 Deploying frontend..."
kubectl apply -f k8s/base/frontend/

echo "🌐 Setting up ingress..."
kubectl apply -f k8s/base/ingress.yaml

echo "⏳ Waiting for deployments..."
kubectl wait --for=condition=available --timeout=300s \
  deployment/backend deployment/frontend -n todo-app

echo "✅ Deployment complete!"
echo "🌍 Access your app at: http://todo.local"
echo "🔍 Check status: kubectl get pods -n todo-app"