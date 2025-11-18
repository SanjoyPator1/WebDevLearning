#!/bin/bash
set -e

echo "🏗️  Building Docker images..."

# Build backend
echo "📦 Building backend image..."
cd todo-app
docker build -t todo-app-backend:latest --target production .
cd ..

# Build frontend
echo "📦 Building frontend image..."
cd todo-app-frontend
docker build -t todo-app-frontend:latest .
cd ..

# Load images into KIND
echo "📥 Loading images into KIND cluster..."
kind load docker-image todo-app-backend:latest --name todo-app-cluster
kind load docker-image todo-app-frontend:latest --name todo-app-cluster

echo "✅ Images built and loaded!"