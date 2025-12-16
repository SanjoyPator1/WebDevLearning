# Kubernetes YAML Syntax Reference

## Basic Pod Structure

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: my-container
    image: nginx
    ports:
    - containerPort: 80
```

_Add more examples as you learn..._
