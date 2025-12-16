# kubectl Cheatsheet

## Common Commands

```bash
# Get resources
kubectl get pods
kubectl get services
kubectl get deployments

# Describe resources
kubectl describe pod <pod-name>

# Logs
kubectl logs <pod-name>
kubectl logs -f <pod-name>

# Execute commands
kubectl exec -it <pod-name> -- bash

# Port forwarding
kubectl port-forward pod/<pod-name> 8080:80
```

_Add more commands as you learn..._
