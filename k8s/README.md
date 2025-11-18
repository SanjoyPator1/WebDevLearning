# Todo App Kubernetes Deployment

Production-grade Kubernetes setup for the Todo App (FastAPI + Next.js).

## Prerequisites

- Docker
- kubectl
- KIND (Kubernetes IN Docker)

Install KIND:

```bash
# On Linux
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# On Mac
brew install kind
```

## Quick Start (Local with KIND)

```bash
# 1. Setup KIND cluster with ingress
cd k8s/scripts
chmod +x *.sh
./setup-kind.sh

# 2. Build and load images
./build-images.sh

# 3. Deploy application
./deploy-local.sh

# 4. Add to /etc/hosts
echo "127.0.0.1 todo.local" | sudo tee -a /etc/hosts

# 5. Access the app
open http://todo.local
```

## Useful Commands

```bash
# Check pods
kubectl get pods -n todo-app

# Check services
kubectl get svc -n todo-app

# View logs
kubectl logs -f deployment/backend -n todo-app
kubectl logs -f deployment/frontend -n todo-app

# Port forward (if ingress not working)
kubectl port-forward svc/frontend 3000:3000 -n todo-app
kubectl port-forward svc/backend 8000:8000 -n todo-app

# Restart deployment
kubectl rollout restart deployment/backend -n todo-app

# Delete everything
./teardown.sh
```

## Architecture

```
┌─────────────┐
│   Ingress   │ (todo.local)
└──────┬──────┘
       │
   ┌───┴────┐
   │        │
┌──▼──┐  ┌─▼────┐
│Front│  │Backend│
│end  │  │(API) │
└─────┘  └───┬──┘
             │
        ┌────▼────┐
        │PostgreSQL│
        └─────────┘
```

## Next Steps for AWS EKS

1. Update image references to ECR
2. Configure AWS ALB Ingress Controller
3. Use AWS RDS instead of PostgreSQL pod
4. Add AWS Secrets Manager integration
5. Configure autoscaling
