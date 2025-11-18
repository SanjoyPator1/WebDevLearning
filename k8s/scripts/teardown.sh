#!/bin/bash
set -e

echo "🗑️  Tearing down todo-app..."

# Delete all resources
kubectl delete namespace todo-app --ignore-not-found=true

# Delete KIND cluster
kind delete cluster --name todo-app-cluster

echo "✅ Cleanup complete!"