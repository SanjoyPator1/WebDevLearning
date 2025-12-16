# Complete Kubernetes Learning Roadmap

## From Absolute Beginner to Advanced (90-Day Plan)

---

## 📋 Overview

This is a structured 90-day roadmap to master Kubernetes from scratch. Each week builds on previous knowledge with hands-on projects to cement your learning.

**Time Commitment**: 2-3 hours per day
**Prerequisites**: Basic Linux commands, understanding of what containers are
**End Goal**: Deploy production-grade applications on Kubernetes with confidence

---

## 🎯 Learning Phases

### Phase 1: Foundation (Week 1-2) - Beginner

**Goal**: Understand containers and Kubernetes basics

### Phase 2: Core Concepts (Week 3-5) - Beginner to Intermediate

**Goal**: Master fundamental Kubernetes objects and operations

### Phase 3: Advanced Deployments (Week 6-8) - Intermediate

**Goal**: Complex deployments, storage, and networking

### Phase 4: Production Readiness (Week 9-11) - Intermediate to Advanced

**Goal**: Monitoring, security, and production best practices

### Phase 5: Advanced Topics (Week 12-13) - Advanced

**Goal**: Service mesh, operators, and advanced patterns

---

## 📅 Detailed Roadmap

---

## WEEK 1: Container Fundamentals & Kubernetes Introduction

### Day 1: Understanding Containers

**Theory (1 hour)**

- What are containers and why do we need them?
- Difference between VMs and containers
- Container use cases and benefits
- Introduction to Docker

**Practice (1-2 hours)**

- Install Docker on your machine
- Run your first container: `docker run hello-world`
- Basic Docker commands:
  ```bash
  docker run -it ubuntu bash
  docker ps
  docker ps -a
  docker images
  docker rm <container-id>
  docker rmi <image-id>
  ```

**Exercise**

- Pull nginx image and run it
- Access nginx in browser
- Stop and remove the container

### Day 2: Docker Deep Dive

**Theory (1 hour)**

- Docker images vs containers
- Docker Hub and registries
- Container lifecycle
- Port mapping and volumes

**Practice (1-2 hours)**

```bash
# Run nginx with port mapping
docker run -d -p 8080:80 nginx

# Run with volume mount
docker run -d -p 8080:80 -v $(pwd)/html:/usr/share/nginx/html nginx

# View logs
docker logs <container-id>

# Execute commands in running container
docker exec -it <container-id> bash
```

**Exercise**

- Create a simple HTML file
- Mount it to nginx container
- Access it in browser

### Day 3: Building Docker Images

**Theory (1 hour)**

- Dockerfile syntax
- Image layers and caching
- Best practices for Dockerfiles
- Multi-stage builds

**Practice (1-2 hours)**
Create a simple Python app:

```python
# app.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Docker!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

```bash
# Build and run
docker build -t my-flask-app .
docker run -p 5000:5000 my-flask-app
```

**Exercise**

- Build your own Flask app image
- Run multiple instances on different ports
- Push image to Docker Hub

### Day 4: Introduction to Kubernetes

**Theory (1 hour)**

- What is Kubernetes and why?
- Kubernetes vs Docker Compose
- Kubernetes architecture overview
  - Control Plane (API Server, Scheduler, Controller Manager, etcd)
  - Worker Nodes (kubelet, kube-proxy, container runtime)
- Kubernetes objects overview

**Practice (1-2 hours)**

- Install kubectl
- Set up local Kubernetes (choose one):

  - **Option A: Minikube** (Recommended)

    ```bash
    # Install minikube
    brew install minikube  # macOS
    # or download from minikube.io

    # Start cluster
    minikube start
    minikube status
    minikube dashboard
    ```

  - **Option B: kind**

    ```bash
    # Install kind
    brew install kind

    # Create cluster
    kind create cluster --name dev-cluster
    ```

  - **Option C: Docker Desktop**
    - Enable Kubernetes in settings

**Exercise**

- Start your local Kubernetes cluster
- Run: `kubectl cluster-info`
- Explore the dashboard
- Run: `kubectl get nodes`

### Day 5: First Kubernetes Deployment

**Theory (1 hour)**

- Pods: The smallest unit in Kubernetes
- Deployments: Managing Pods
- Services: Exposing applications
- kubectl basics

**Practice (1-2 hours)**

```bash
# Imperative approach
kubectl run nginx --image=nginx --port=80
kubectl get pods
kubectl describe pod nginx
kubectl logs nginx
kubectl delete pod nginx

# Declarative approach
# Create nginx-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx
    ports:
    - containerPort: 80
```

```bash
kubectl apply -f nginx-pod.yaml
kubectl get pods
kubectl port-forward pod/nginx 8080:80
# Visit http://localhost:8080
```

**Exercise**

- Deploy your Flask app from Day 3 as a Pod
- Access it using port-forward
- Check logs and describe the pod

### Day 6-7: Weekend Project 1 - Deploy Multi-Container App

**Project: Simple Blog Application**

Deploy a WordPress blog with MySQL database.

**Components**:

1. MySQL database pod
2. WordPress application pod
3. Connect them together

**Steps**:

```yaml
# mysql-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql
  labels:
    app: mysql
spec:
  containers:
    - name: mysql
      image: mysql:8.0
      env:
        - name: MYSQL_ROOT_PASSWORD
          value: "rootpassword"
        - name: MYSQL_DATABASE
          value: "wordpress"
        - name: MYSQL_USER
          value: "wpuser"
        - name: MYSQL_PASSWORD
          value: "wppassword"
      ports:
        - containerPort: 3306

---
# wordpress-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: wordpress
  labels:
    app: wordpress
spec:
  containers:
    - name: wordpress
      image: wordpress:latest
      env:
        - name: WORDPRESS_DB_HOST
          value: "mysql"
        - name: WORDPRESS_DB_USER
          value: "wpuser"
        - name: WORDPRESS_DB_PASSWORD
          value: "wppassword"
        - name: WORDPRESS_DB_NAME
          value: "wordpress"
      ports:
        - containerPort: 80
```

**Challenges**:

- Why can't WordPress connect to MySQL?
- What's missing? (Hint: Services)
- Document your learnings

**Deliverables**:

- GitHub repo with your YAML files
- README explaining what you learned
- Screenshots of running application

---

## WEEK 2: Kubernetes Core Objects

### Day 8: Deployments

**Theory (1 hour)**

- Why Deployments over Pods?
- Replica management
- Rolling updates and rollbacks
- Deployment strategies
- Self-healing

**Practice (1-2 hours)**

```yaml
# nginx-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.21
          ports:
            - containerPort: 80
```

```bash
kubectl apply -f nginx-deployment.yaml
kubectl get deployments
kubectl get pods
kubectl get rs  # ReplicaSets

# Scale
kubectl scale deployment nginx-deployment --replicas=5

# Update image
kubectl set image deployment/nginx-deployment nginx=nginx:1.22

# Check rollout status
kubectl rollout status deployment/nginx-deployment

# View history
kubectl rollout history deployment/nginx-deployment

# Rollback
kubectl rollout undo deployment/nginx-deployment
```

**Exercise**

- Create deployment with 3 replicas
- Delete one pod and watch it recreate
- Update to new image version
- Rollback to previous version

### Day 9: Services

**Theory (1 hour)**

- Service types: ClusterIP, NodePort, LoadBalancer
- Service discovery
- Endpoints
- Selectors and labels

**Practice (1-2 hours)**

```yaml
# nginx-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
```

```bash
kubectl apply -f nginx-service.yaml
kubectl get services
kubectl describe service nginx-service

# Access service
minikube service nginx-service  # Opens in browser
# or
kubectl port-forward service/nginx-service 8080:80
```

**Types to practice**:

```yaml
# ClusterIP (default - internal only)
type: ClusterIP

# NodePort (exposes on node IP)
type: NodePort

# LoadBalancer (cloud provider)
type: LoadBalancer
```

**Exercise**

- Create service for your previous deployment
- Access via NodePort
- Try all three service types

### Day 10: Labels and Selectors

**Theory (1 hour)**

- Label best practices
- Selectors (equality-based, set-based)
- Annotations vs Labels
- Common label patterns

**Practice (1-2 hours)**

```yaml
metadata:
  labels:
    app: myapp
    tier: frontend
    environment: production
    version: v1.2.0
    team: platform
```

```bash
# Get resources by label
kubectl get pods -l app=nginx
kubectl get pods -l environment=production,tier=frontend
kubectl get pods -l 'environment in (production,staging)'

# Add labels
kubectl label pod nginx-pod version=v1.0.0

# Remove labels
kubectl label pod nginx-pod version-

# Show labels
kubectl get pods --show-labels
kubectl get pods -L app,version
```

**Exercise**

- Label your pods with app, env, version
- Query pods using different selectors
- Update service to use specific labels

### Day 11: Namespaces

**Theory (1 hour)**

- What are namespaces?
- Default namespaces (default, kube-system, kube-public)
- Resource isolation
- Resource quotas per namespace
- Network policies per namespace

**Practice (1-2 hours)**

```bash
# List namespaces
kubectl get namespaces

# Create namespace
kubectl create namespace development
kubectl create namespace staging
kubectl create namespace production

# Or using YAML
apiVersion: v1
kind: Namespace
metadata:
  name: testing
```

```yaml
# Deploy to specific namespace
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: development
spec:
  # ... rest of spec
```

```bash
# Apply to namespace
kubectl apply -f deployment.yaml -n development

# Get resources from namespace
kubectl get pods -n development
kubectl get all -n development

# Set default namespace
kubectl config set-context --current --namespace=development

# Get resources from all namespaces
kubectl get pods --all-namespaces
kubectl get pods -A
```

**Exercise**

- Create dev, staging, prod namespaces
- Deploy same application to each
- Practice switching between namespaces

### Day 12: ConfigMaps and Secrets

**Theory (1 hour)**

- Separating config from code
- ConfigMaps for non-sensitive data
- Secrets for sensitive data
- Different ways to consume them

**Practice (1-2 hours)**

**ConfigMaps**:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_NAME: "My Application"
  LOG_LEVEL: "info"
  DATABASE_HOST: "mysql-service"
  config.json: |
    {
      "feature_flags": {
        "new_ui": true,
        "beta_features": false
      }
    }
```

```bash
# Create from literal
kubectl create configmap app-config \
  --from-literal=APP_NAME="My App" \
  --from-literal=LOG_LEVEL=debug

# Create from file
kubectl create configmap nginx-config --from-file=nginx.conf
```

**Using ConfigMap**:

```yaml
spec:
  containers:
    - name: app
      image: myapp
      # Method 1: All keys as env vars
      envFrom:
        - configMapRef:
            name: app-config

      # Method 2: Specific key as env var
      env:
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_NAME

      # Method 3: Mount as volume
      volumeMounts:
        - name: config-volume
          mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: app-config
```

**Secrets**:

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DATABASE_PASSWORD: "supersecret"
  API_KEY: "my-api-key"
# Or use data with base64
data:
  username: YWRtaW4= # admin in base64
```

```bash
# Create secret
kubectl create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=secret123

# Encode/decode
echo -n "mysecret" | base64
echo "bXlzZWNyZXQ=" | base64 -d
```

**Exercise**

- Create ConfigMap with application settings
- Create Secret with database credentials
- Deploy app using both
- Verify environment variables in pod

### Day 13-14: Weekend Project 2 - Todo Application with Database

**Project: Full-Stack Todo App**

Build a complete todo application with:

1. React frontend (or simple HTML/JS)
2. FastAPI/Flask backend
3. PostgreSQL database
4. All properly configured using ConfigMaps and Secrets

**Architecture**:

```
[Frontend Pod] ---> [Backend Service] ---> [Backend Pod]
                                              |
                                              v
                                      [Database Service] ---> [Database Pod]
```

**Requirements**:

- Use Deployments (not Pods)
- Proper Services for each component
- ConfigMaps for application configuration
- Secrets for database credentials
- Multiple replicas for frontend and backend
- Proper labels and namespaces

**Bonus Challenges**:

- Add health check endpoints
- Implement proper logging
- Use environment-specific configs (dev namespace)

**Deliverables**:

- Complete YAML manifests
- Application code
- README with architecture diagram
- Instructions to deploy

---

## WEEK 3: Storage and Persistence

### Day 15: Understanding Kubernetes Storage

**Theory (1 hour)**

- Ephemeral vs Persistent storage
- Volumes overview
- Volume types (emptyDir, hostPath, etc.)
- Storage use cases

**Practice (1-2 hours)**

**EmptyDir (Temporary storage)**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: cache
          mountPath: /cache
    - name: sidecar
      image: busybox
      command: ["sh", "-c", "tail -f /dev/null"]
      volumeMounts:
        - name: cache
          mountPath: /cache
  volumes:
    - name: cache
      emptyDir: {}
```

**HostPath (Node storage - dev only)**:

```yaml
volumes:
  - name: data
    hostPath:
      path: /data
      type: DirectoryOrCreate
```

**Exercise**

- Create pod with emptyDir volume
- Share data between two containers
- Test data persistence when pod restarts

### Day 16: Persistent Volumes (PV) and Claims (PVC)

**Theory (1 hour)**

- PersistentVolume (PV)
- PersistentVolumeClaim (PVC)
- Storage Classes
- Access Modes (ReadWriteOnce, ReadOnlyMany, ReadWriteMany)
- Reclaim Policies

**Practice (1-2 hours)**

```yaml
# pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  hostPath:
    path: /mnt/data/mysql

---
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: manual

---
# Using PVC in pod
spec:
  containers:
    - name: mysql
      image: mysql:8.0
      volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
  volumes:
    - name: mysql-storage
      persistentVolumeClaim:
        claimName: mysql-pvc
```

```bash
kubectl apply -f pv.yaml
kubectl apply -f pvc.yaml
kubectl get pv
kubectl get pvc
```

**Exercise**

- Create PV and PVC
- Deploy MySQL with persistent storage
- Delete pod and verify data persists
- Create new pod and confirm data is there

### Day 17: StatefulSets

**Theory (1 hour)**

- StatefulSets vs Deployments
- Stable network identities
- Ordered deployment and scaling
- VolumeClaimTemplates
- Headless services

**Practice (1-2 hours)**

```yaml
# headless-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
    - port: 3306

---
# statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-headless
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              value: rootpass
          ports:
            - containerPort: 3306
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 5Gi
```

**StatefulSet Features**:

- Pods get predictable names: `mysql-0`, `mysql-1`, `mysql-2`
- DNS entries: `mysql-0.mysql-headless.default.svc.cluster.local`
- Each pod gets its own PVC

```bash
kubectl apply -f headless-service.yaml
kubectl apply -f statefulset.yaml
kubectl get statefulsets
kubectl get pods -l app=mysql
kubectl get pvc
```

**Exercise**

- Deploy StatefulSet with 3 replicas
- Check pod names and PVCs
- Delete a pod and watch ordered recreation
- Scale up and down

### Day 18: Storage Classes and Dynamic Provisioning

**Theory (1 hour)**

- Dynamic provisioning
- Storage Classes
- Default storage class
- Provisioners (AWS EBS, GCE PD, Azure Disk, etc.)
- Volume expansion

**Practice (1-2 hours)**

```yaml
# storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-storage
provisioner: kubernetes.io/no-provisioner # For local testing
volumeBindingMode: WaitForFirstConsumer
```

```bash
# Check available storage classes
kubectl get storageclass

# For minikube, use default provisioner
minikube addons enable storage-provisioner
```

**Dynamic PVC**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard # Uses default provisioner
  resources:
    requests:
      storage: 1Gi
```

**Exercise**

- List storage classes in your cluster
- Create PVC without manually creating PV
- Deploy application using dynamic PVC
- Verify PV was created automatically

### Day 19: Init Containers and Multi-Container Patterns

**Theory (1 hour)**

- Init containers
- Sidecar pattern
- Ambassador pattern
- Adapter pattern
- Container lifecycle

**Practice (1-2 hours)**

**Init Container**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  initContainers:
    - name: init-db
      image: busybox
      command:
        [
          "sh",
          "-c",
          "until nslookup mysql-service; do echo waiting for mysql; sleep 2; done",
        ]

    - name: init-data
      image: busybox
      command: ["sh", "-c", 'echo "Initializing data..." && sleep 5']

  containers:
    - name: app
      image: myapp:latest
```

**Sidecar Pattern** (Log shipping):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  containers:
    # Main application
    - name: app
      image: myapp
      volumeMounts:
        - name: logs
          mountPath: /var/log/app

    # Sidecar: Log shipper
    - name: log-shipper
      image: fluent/fluent-bit
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
          readOnly: true

  volumes:
    - name: logs
      emptyDir: {}
```

**Exercise**

- Create pod with init container that waits for service
- Implement sidecar pattern for log processing
- Verify init containers run before main container

### Day 20-21: Weekend Project 3 - Stateful Blog Platform

**Project: WordPress with MySQL StatefulSet**

Deploy production-like WordPress with:

1. MySQL StatefulSet (3 replicas with replication)
2. WordPress Deployment (3 replicas)
3. Persistent storage for both
4. Proper service configuration

**Advanced Requirements**:

- Use StatefulSet for MySQL
- Implement MySQL replication (primary-replica setup)
- Use PersistentVolumeClaims
- ConfigMap for WordPress settings
- Secret for database credentials
- Init container to wait for database
- Health checks for both components

**Architecture**:

```
[LoadBalancer Service] ---> [WordPress Deployment (3 replicas)]
                                     |
                                     v
                            [MySQL Headless Service]
                                     |
                   +-----------------+-----------------+
                   v                 v                 v
               [mysql-0]         [mysql-1]         [mysql-2]
                  |                 |                 |
               [PVC-0]           [PVC-1]           [PVC-2]
```

**Bonus Challenges**:

- Implement automated backups using CronJob
- Add Redis cache as sidecar
- Configure proper resource limits
- Test failover scenarios

**Deliverables**:

- Complete infrastructure as code
- MySQL replication configuration
- Disaster recovery plan
- Load testing results

---

## WEEK 4: Networking Deep Dive

### Day 22: Kubernetes Networking Fundamentals

**Theory (1 hour)**

- Kubernetes networking model
- Pod-to-Pod communication
- Pod-to-Service communication
- External-to-Service communication
- CNI (Container Network Interface)
- Network policies overview

**Practice (1-2 hours)**

```bash
# Check network configuration
kubectl get nodes -o wide
kubectl get pods -o wide

# Test pod-to-pod communication
kubectl run test-1 --image=busybox -- sleep 3600
kubectl run test-2 --image=busybox -- sleep 3600

# Get pod IPs
kubectl get pods -o wide

# Exec into pod and ping another
kubectl exec -it test-1 -- ping <test-2-ip>

# Test DNS
kubectl exec -it test-1 -- nslookup kubernetes.default
```

**Exercise**

- Deploy two pods in same namespace
- Test direct IP communication
- Deploy pods in different namespaces
- Test cross-namespace communication

### Day 23: Ingress Controllers

**Theory (1 hour)**

- What is Ingress?
- Ingress vs Service
- Ingress Controllers (Nginx, Traefik, HAProxy)
- Ingress rules and paths
- TLS/SSL termination

**Practice (1-2 hours)**

**Install Nginx Ingress Controller**:

```bash
# For minikube
minikube addons enable ingress

# Or manually
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
```

**Simple Ingress**:

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: simple-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-service
                port:
                  number: 80
```

**Path-based routing**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8000
          - path: /admin
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 3000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

**TLS Ingress**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - myapp.local
      secretName: tls-secret
  rules:
    - host: myapp.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-service
                port:
                  number: 80
```

```bash
# Create TLS secret
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=myapp.local"

kubectl create secret tls tls-secret --cert=tls.crt --key=tls.key
```

**Exercise**

- Deploy two different applications
- Create Ingress with path-based routing
- Test accessing /app1 and /app2
- Add TLS to your Ingress

### Day 24: Network Policies

**Theory (1 hour)**

- Default allow behavior
- Network policy specification
- Ingress and Egress rules
- Pod selectors and namespace selectors
- Common security patterns

**Practice (1-2 hours)**

**Allow all traffic** (default behavior):

```yaml
# No network policy = all traffic allowed
```

**Deny all ingress**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

**Allow specific ingress**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8000
```

**Allow from specific namespace**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress-namespace
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
```

**Egress policy** (control outbound):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-egress
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Egress
  egress:
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow database
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

**Exercise**

- Create network policy that denies all traffic
- Create policy allowing specific pod-to-pod communication
- Test with curl between pods
- Implement three-tier app with network policies

### Day 25: DNS and Service Discovery

**Theory (1 hour)**

- CoreDNS in Kubernetes
- Service DNS names
- Pod DNS names
- DNS for services in different namespaces
- Custom DNS configuration

**Practice (1-2 hours)**

**DNS naming patterns**:

```
# Service DNS
<service-name>.<namespace>.svc.cluster.local

# Pod DNS
<pod-ip-with-dashes>.<namespace>.pod.cluster.local

# Headless service pod
<pod-name>.<service-name>.<namespace>.svc.cluster.local
```

**Testing DNS**:

```bash
# Deploy test pod
kubectl run dnsutils --image=gcr.io/kubernetes-e2e-test-images/dnsutils:1.3 \
  --command -- sleep 3600

# Test DNS resolution
kubectl exec -it dnsutils -- nslookup kubernetes.default
kubectl exec -it dnsutils -- nslookup myservice.default.svc.cluster.local
kubectl exec -it dnsutils -- dig myservice.default.svc.cluster.local
```

**Custom DNS**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-dns-pod
spec:
  dnsPolicy: "None"
  dnsConfig:
    nameservers:
      - 8.8.8.8
    searches:
      - my.custom.domain
    options:
      - name: ndots
        value: "2"
  containers:
    - name: app
      image: nginx
```

**Exercise**

- Deploy service and test DNS from another pod
- Query service in different namespace
- Test DNS with StatefulSet pods
- Configure custom DNS for specific pod

### Day 26: Service Mesh Introduction (Istio Basics)

**Theory (1 hour)**

- What is a service mesh?
- Why service mesh?
- Istio architecture (Control plane, Data plane)
- Sidecars (Envoy proxy)
- Service mesh capabilities

**Practice (1-2 hours)**

**Install Istio** (simplified):

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install
istioctl install --set profile=demo -y

# Enable automatic sidecar injection
kubectl label namespace default istio-injection=enabled
```

**Deploy sample app**:

```bash
# Deploy bookinfo sample
kubectl apply -f samples/bookinfo/platform/kube/bookinfo.yaml

# Check services
kubectl get services
kubectl get pods

# Check sidecar injection
kubectl get pods -l app=ratings -o jsonpath='{.items[0].spec.containers[*].name}'
```

**Exercise**

- Install Istio on your cluster
- Deploy application with automatic sidecar injection
- Verify Envoy sidecars are running
- Explore Istio dashboard

### Day 27-28: Weekend Project 4 - Microservices E-Commerce Platform

**Project: Complete E-Commerce Backend**

Build a microservices-based e-commerce platform with proper networking.

**Services**:

1. **Frontend Service** (React/Vue or simple HTML)
2. **API Gateway** (Kong or custom)
3. **User Service** (Authentication/Authorization)
4. **Product Service** (Product catalog)
5. **Order Service** (Order management)
6. **Inventory Service** (Stock management)
7. **PostgreSQL** (Database)
8. **Redis** (Cache)

**Architecture**:

```
                        [Ingress]
                            |
                            v
                      [Frontend] (Public)
                            |
                            v
                      [API Gateway]
                            |
        +-------------------+-------------------+
        v                   v                   v
    [User Svc]         [Product Svc]       [Order Svc]
        |                   |                   |
        +-------------------+-------------------+
                            v
                        [Postgres]
```

**Requirements**:

- Use Deployments for all services
- Implement proper Services (ClusterIP for internal)
- Use Ingress for external access
- Network Policies for security:
  - Frontend can only access API Gateway
  - Services can only access what they need
  - Database only accessible by backend services
- ConfigMaps for configuration
- Secrets for credentials
- Health checks for all services
- At least 2 replicas for each service

**Advanced Requirements**:

- Service mesh integration (Istio)
- Distributed tracing
- Circuit breakers
- Rate limiting
- JWT authentication

**Deliverables**:

- Complete microservices code
- K8s manifests for all components
- Network policy definitions
- Architecture documentation
- API documentation
- Test scenarios

---

## WEEK 5: Configuration and Security

### Day 29: Advanced ConfigMaps and Secrets

**Theory (1 hour)**

- Secret types (Opaque, TLS, Docker registry)
- External secret management (Vault, AWS Secrets Manager)
- Sealed Secrets
- Secret rotation
- Best practices

**Practice (1-2 hours)**

**Secret Types**:

```yaml
# Opaque secret
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  username: admin
  password: supersecret

---
# TLS secret
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
type: kubernetes.io/tls
data:
  tls.crt: <base64-cert>
  tls.key: <base64-key>

---
# Docker registry secret
apiVersion: v1
kind: Secret
metadata:
  name: docker-secret
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: <base64-encoded-docker-config>
```

**Using Docker registry secret**:

```yaml
spec:
  imagePullSecrets:
    - name: docker-secret
  containers:
    - name: app
      image: private-registry.com/myapp:latest
```

**Sealed Secrets** (for GitOps):

```bash
# Install kubeseal
brew install kubeseal

# Create sealed secret
kubectl create secret generic my-secret \
  --from-literal=password=supersecret \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Safe to commit to Git
kubectl apply -f sealed-secret.yaml
```

**Exercise**

- Create different types of secrets
- Use Docker registry secret for private image
- Install and use Sealed Secrets
- Implement secret rotation strategy

### Day 30: Resource Management

**Theory (1 hour)**

- Resource requests vs limits
- CPU and memory units
- QoS classes (Guaranteed, Burstable, BestEffort)
- ResourceQuotas
- LimitRanges
- PodDisruptionBudgets

**Practice (1-2 hours)**

**Resource requests and limits**:

```yaml
spec:
  containers:
    - name: app
      image: myapp
      resources:
        requests:
          memory: "64Mi"
          cpu: "250m" # 0.25 CPU
        limits:
          memory: "128Mi"
          cpu: "500m" # 0.5 CPU
```

**QoS Classes**:

```yaml
# Guaranteed (requests = limits)
resources:
  requests:
    memory: "128Mi"
    cpu: "500m"
  limits:
    memory: "128Mi"
    cpu: "500m"

# Burstable (requests < limits)
resources:
  requests:
    memory: "64Mi"
    cpu: "250m"
  limits:
    memory: "128Mi"
    cpu: "500m"

# BestEffort (no requests/limits)
# No resources specified
```

**ResourceQuota**:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: development
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    persistentvolumeclaims: "10"
    pods: "50"
```

**LimitRange**:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: mem-limit-range
  namespace: development
spec:
  limits:
    - max:
        memory: "1Gi"
        cpu: "1"
      min:
        memory: "64Mi"
        cpu: "100m"
      default:
        memory: "256Mi"
        cpu: "500m"
      defaultRequest:
        memory: "128Mi"
        cpu: "250m"
      type: Container
```

**PodDisruptionBudget**:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

**Exercise**

- Deploy app with resource requests and limits
- Test OOMKilled scenario (exceed memory limit)
- Create ResourceQuota for namespace
- Implement LimitRange

### Day 31: RBAC (Role-Based Access Control)

**Theory (1 hour)**

- Authentication vs Authorization
- Users, Groups, ServiceAccounts
- Roles and ClusterRoles
- RoleBindings and ClusterRoleBindings
- RBAC best practices

**Practice (1-2 hours)**

**ServiceAccount**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**Role** (namespace-scoped):

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
```

**RoleBinding**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
  - kind: ServiceAccount
    name: my-service-account
    namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**ClusterRole** (cluster-wide):

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
```

**ClusterRoleBinding**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
  - kind: ServiceAccount
    name: my-service-account
    namespace: default
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

**Using ServiceAccount in Pod**:

```yaml
spec:
  serviceAccountName: my-service-account
  containers:
    - name: app
      image: myapp
```

**Testing RBAC**:

```bash
# Check permissions
kubectl auth can-i get pods --as=system:serviceaccount:default:my-service-account
kubectl auth can-i create deployments --as=system:serviceaccount:default:my-service-account

# Impersonate user
kubectl get pods --as=system:serviceaccount:default:my-service-account
```

**Exercise**

- Create ServiceAccount for application
- Create Role with limited permissions
- Bind Role to ServiceAccount
- Deploy pod with ServiceAccount
- Test permission boundaries

### Day 32: Security Contexts and Pod Security

**Theory (1 hour)**

- Security contexts
- Pod Security Standards (Privileged, Baseline, Restricted)
- Pod Security Admission
- AppArmor and SELinux
- Seccomp profiles

**Practice (1-2 hours)**

**Pod Security Context**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-demo
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
    - name: app
      image: busybox
      command: ["sh", "-c", "sleep 3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        runAsNonRoot: true
        capabilities:
          drop:
            - ALL
```

**Pod Security Standards**:

```yaml
# Namespace with restricted policy
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Example secure deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: secure-app
  template:
    metadata:
      labels:
        app: secure-app
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: myapp:latest
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /app/cache
      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}
```

**Exercise**

- Create pod with security context
- Test running as non-root user
- Implement read-only root filesystem
- Apply Pod Security Standards to namespace

### Day 33: Jobs and CronJobs

**Theory (1 hour)**

- Job patterns (one-shot, parallel, work queue)
- CronJobs for scheduled tasks
- Job completion and failures
- Backoff and retry logic
- Cleaning up finished jobs

**Practice (1-2 hours)**

**Simple Job**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: database-backup
spec:
  template:
    spec:
      containers:
        - name: backup
          image: postgres:15
          command:
            - /bin/sh
            - -c
            - pg_dump $DATABASE_URL > /backup/db-$(date +%Y%m%d).sql
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: url
          volumeMounts:
            - name: backup-storage
              mountPath: /backup
      restartPolicy: OnFailure
      volumes:
        - name: backup-storage
          persistentVolumeClaim:
            claimName: backup-pvc
  backoffLimit: 4
```

**Parallel Job**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processing
spec:
  parallelism: 5 # Run 5 pods at a time
  completions: 20 # Complete 20 tasks total
  template:
    spec:
      containers:
        - name: processor
          image: data-processor:latest
      restartPolicy: OnFailure
```

**CronJob**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-backup
spec:
  schedule: "0 2 * * *" # Every day at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: backup-tool:latest
              command:
                - /backup.sh
          restartPolicy: OnFailure
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
```

**Cron Schedule Examples**:

```
"*/5 * * * *"     # Every 5 minutes
"0 * * * *"       # Every hour
"0 */6 * * *"     # Every 6 hours
"0 2 * * *"       # Daily at 2 AM
"0 0 * * 0"       # Weekly (Sunday midnight)
"0 0 1 * *"       # Monthly (1st at midnight)
"0 0 1 1 *"       # Yearly (Jan 1st)
```

**Exercise**

- Create Job for database migration
- Create CronJob for daily cleanup
- Test parallel job execution
- Implement job with retry logic

### Day 34-35: Weekend Project 5 - Production-Grade Application

**Project: Multi-Tenant SaaS Platform**

Build a production-ready multi-tenant application with complete security and configuration management.

**Requirements**:

**Core Application**:

1. API Gateway (with rate limiting)
2. Authentication Service (JWT-based)
3. Application Backend (Python/Node.js)
4. Database (PostgreSQL with replication)
5. Cache (Redis cluster)
6. Background Workers (Celery/Bull)

**Security & Configuration**:

- RBAC for all components
- Network Policies (zero-trust model)
- Pod Security Standards (Restricted)
- Secrets management (Sealed Secrets)
- TLS everywhere
- Security contexts on all pods

**Resource Management**:

- ResourceQuotas per tenant namespace
- LimitRanges configured
- Resource requests and limits on all pods
- PodDisruptionBudgets for high availability

**Monitoring & Operations**:

- Health checks (liveness, readiness, startup)
- Jobs for database migrations
- CronJobs for cleanup and backups
- Proper logging configuration

**Architecture**:

```
[Ingress (TLS)] ---> [Auth Service] ---> [API Gateway]
                                              |
                    +-------------------------+-------------------------+
                    v                         v                         v
              [App Service]              [Worker Service]          [Admin Service]
                    |                         |                         |
                    +-------------------------+-------------------------+
                                              v
                                    [PostgreSQL StatefulSet]
                                              |
                                        [Redis Cluster]
```

**Deliverables**:

- Complete application code
- Comprehensive K8s manifests
- Security policies and RBAC rules
- CI/CD pipeline (GitHub Actions)
- Monitoring and alerting setup
- Disaster recovery plan
- Performance testing results
- Complete documentation

---

## WEEK 6-7: Scaling and Performance

### Day 36: Horizontal Pod Autoscaling (HPA)

**Theory (1 hour)**

- Metrics Server
- HPA v2 API
- CPU-based scaling
- Memory-based scaling
- Custom metrics
- Scaling policies

**Practice (1-2 hours)**

**Install Metrics Server**:

```bash
# Minikube
minikube addons enable metrics-server

# Or manually
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**Simple CPU-based HPA**:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Multi-metric HPA**:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: advanced-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

**Testing HPA**:

```bash
# Generate load
kubectl run -it load-generator --rm --image=busybox --restart=Never -- /bin/sh

# Inside the pod
while true; do wget -q -O- http://myapp-service; done

# Watch HPA
kubectl get hpa -w

# Check metrics
kubectl top nodes
kubectl top pods
```

**Exercise**

- Deploy application with resource requests
- Create HPA based on CPU
- Generate load and watch scaling
- Configure custom scaling policies

### Day 37: Vertical Pod Autoscaling (VPA)

**Theory (1 hour)**

- VPA vs HPA
- VPA modes (Off, Initial, Auto)
- Resource recommendations
- When to use VPA

**Practice (1-2 hours)**

**Install VPA**:

```bash
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh
```

**VPA Configuration**:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: myapp-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  updatePolicy:
    updateMode: "Auto" # or "Off", "Initial"
  resourcePolicy:
    containerPolicies:
      - containerName: app
        minAllowed:
          cpu: 100m
          memory: 50Mi
        maxAllowed:
          cpu: 1
          memory: 500Mi
```

**VPA Modes**:

- `Off`: Only recommendations, no updates
- `Initial`: Sets resources on pod creation only
- `Auto`: Updates resources on existing pods (requires restart)

**Exercise**

- Install VPA in your cluster
- Deploy app with VPA in recommendation mode
- Analyze resource recommendations
- Enable auto mode and observe changes

### Day 38: Cluster Autoscaling

**Theory (1 hour)**

- Cluster Autoscaler
- Cloud provider integration
- Node pools and instance types
- Scale up and scale down policies
- Pod priorities and preemption

**Practice (1-2 hours)**

**Pod Priority Classes**:

```yaml
# High priority
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority for critical services"

---
# Low priority
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 100
globalDefault: false
description: "Low priority for batch jobs"
```

**Using Priority in Pods**:

```yaml
spec:
  priorityClassName: high-priority
  containers:
    - name: app
      image: myapp
```

**Node Affinity** (influence scheduling):

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: instance-type
                operator: In
                values:
                  - high-memory
                  - high-cpu
```

**Pod Anti-Affinity** (spread pods):

```yaml
spec:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app: myapp
            topologyKey: kubernetes.io/hostname
```

**Exercise**

- Create priority classes
- Deploy high and low priority workloads
- Test node affinity rules
- Implement pod anti-affinity for HA

### Day 39: Performance Optimization

**Theory (1 hour)**

- Container image optimization
- Resource tuning
- Readiness gates
- Topology aware routing
- Performance testing

**Practice (1-2 hours)**

**Optimize Docker Image**:

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

**Readiness Gates**:

```yaml
spec:
  readinessGates:
    - conditionType: "example.com/feature-1"
  containers:
    - name: app
      image: myapp
```

**Topology Spread Constraints**:

```yaml
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: kubernetes.io/hostname
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: myapp
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: ScheduleAnyway
      labelSelector:
        matchLabels:
          app: myapp
```

**Performance Testing**:

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Run load test
hey -z 30s -c 50 http://myapp-service/api/endpoint

# Or use Apache Bench
ab -n 10000 -c 100 http://myapp-service/
```

**Exercise**

- Optimize your application image
- Implement topology spread constraints
- Run performance tests before and after optimization
- Document performance improvements

### Day 40: Monitoring with Prometheus

**Theory (1 hour)**

- Prometheus architecture
- Metrics types (Counter, Gauge, Histogram, Summary)
- PromQL basics
- ServiceMonitor
- Alerting

**Practice (1-2 hours)**

**Install Prometheus Stack**:

```bash
# Add helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

**ServiceMonitor**:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp-metrics
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  endpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

**Expose metrics in your app** (Python example):

```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import FastAPI, Response

app = FastAPI()

# Metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**PromQL Queries**:

```promql
# Request rate
rate(requests_total[5m])

# Average response time
rate(request_duration_seconds_sum[5m]) / rate(request_duration_seconds_count[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))

# Pod memory usage
container_memory_usage_bytes{pod=~"myapp-.*"}

# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"myapp-.*"}[5m])
```

**Exercise**

- Install Prometheus stack
- Add metrics to your application
- Create ServiceMonitor
- Query metrics using PromQL

### Day 41: Logging with ELK/Loki

**Theory (1 hour)**

- Centralized logging
- Loki vs ELK stack
- Log aggregation patterns
- Log levels and structured logging

**Practice (1-2 hours)**

**Install Loki Stack**:

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set grafana.enabled=true
```

**Structured Logging** (Python):

```python
import structlog

logger = structlog.get_logger()

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    logger.info("user_request", user_id=user_id, action="get")
    # ... handle request
    logger.info("user_response", user_id=user_id, status="success")
```

**Log to stdout** (K8s best practice):

```python
import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s'
)
```

**Query logs in Grafana**:

```logql
# All logs from app
{app="myapp"}

# Error logs only
{app="myapp"} |= "error"

# JSON parsing
{app="myapp"} | json | level="error"

# Rate of errors
rate({app="myapp"} |= "error" [5m])
```

**Exercise**

- Install Loki and Grafana
- Implement structured logging
- View logs in Grafana
- Create log-based alerts

### Day 42-43: Weekend Project 6 - Auto-Scaling Web Application

**Project: High-Performance News Aggregator**

Build a scalable news aggregation platform that automatically scales based on traffic.

**Components**:

1. **Web Scraper** (CronJob) - Collects news every hour
2. **API Service** (Deployment with HPA) - Serves aggregated news
3. **Cache Layer** (Redis cluster) - Reduces database load
4. **Database** (PostgreSQL StatefulSet) - Stores articles
5. **Search Service** (Elasticsearch) - Full-text search
6. **Admin Dashboard** - Management interface

**Requirements**:

**Scaling**:

- HPA for API service (CPU and memory based)
- VPA for database and search services
- Cluster autoscaling configuration
- Load testing and capacity planning

**Performance**:

- Redis caching strategy
- Database query optimization
- CDN integration (via Ingress)
- Image optimization
- API response time < 100ms (p95)

**Monitoring**:

- Prometheus metrics
- Grafana dashboards
- Alert rules
- Log aggregation with Loki
- Distributed tracing (Jaeger)

**High Availability**:

- Multiple replicas for all services
- Pod anti-affinity rules
- PodDisruptionBudgets
- Health checks with proper thresholds
- Graceful shutdown handling

**Testing**:

- Load testing plan
- Chaos engineering tests (kill pods, network delays)
- Performance benchmarks
- Cost optimization analysis

**Deliverables**:

- Complete application with auto-scaling
- Load testing results and graphs
- Monitoring dashboards
- Scaling policies documentation
- Performance optimization report
- Cost analysis and recommendations

---

## WEEK 8-9: Advanced Deployments and GitOps

### Day 44: Advanced Deployment Strategies

**Theory (1 hour)**

- Rolling updates (default)
- Blue-Green deployments
- Canary deployments
- A/B testing
- Feature flags

**Practice (1-2 hours)**

**Rolling Update** (default):

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
```

**Blue-Green Deployment**:

```yaml
# Blue deployment (current)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
        - name: app
          image: myapp:v1.0

---
# Green deployment (new)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: green
  template:
    metadata:
      labels:
        app: myapp
        version: green
    spec:
      containers:
        - name: app
          image: myapp:v2.0

---
# Service (switch by changing selector)
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp
    version: blue # Change to 'green' to switch
  ports:
    - port: 80
```

**Canary Deployment** (with Istio):

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
    - myapp.example.com
  http:
    - match:
        - headers:
            user-type:
              exact: beta
      route:
        - destination:
            host: myapp-service
            subset: v2
    - route:
        - destination:
            host: myapp-service
            subset: v1
          weight: 90
        - destination:
            host: myapp-service
            subset: v2
          weight: 10
```

**Exercise**

- Implement blue-green deployment
- Practice switching traffic
- Set up canary deployment with traffic split
- Measure rollback time

### Day 45: Introduction to Helm

**Theory (1 hour)**

- What is Helm?
- Charts, Releases, Repositories
- Helm vs kubectl
- When to use Helm

**Practice (1-2 hours)**

**Install Helm**:

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

**Using Helm**:

```bash
# Add repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Search charts
helm search repo wordpress

# Install chart
helm install my-wordpress bitnami/wordpress \
  --namespace wordpress --create-namespace

# List releases
helm list
helm list --all-namespaces

# Get values
helm show values bitnami/wordpress

# Upgrade
helm upgrade my-wordpress bitnami/wordpress \
  --set wordpressUsername=admin

# Rollback
helm rollback my-wordpress

# Uninstall
helm uninstall my-wordpress
```

**Exercise**

- Install Helm
- Deploy WordPress using Helm
- Customize installation with custom values
- Practice upgrade and rollback

### Day 46-47: Creating Helm Charts

**Theory (1 hour each day)**

- Chart structure
- Templates and values
- Template functions
- Hooks and tests
- Chart dependencies

**Practice (2-3 hours each day)**

**Create Chart**:

```bash
helm create myapp-chart
cd myapp-chart
```

**Chart Structure**:

```
myapp-chart/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── _helpers.tpl
│   └── NOTES.txt
└── charts/
```

**values.yaml**:

```yaml
replicaCount: 2

image:
  repository: myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: myapp.local
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  - name: APP_ENV
    value: production
```

**templates/deployment.yaml**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "myapp.selectorLabels" . | nindent 8 }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: 8000
        {{- with .Values.env }}
        env:
          {{- toYaml . | nindent 12 }}
        {{- end }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
```

**Template Functions**:

```yaml
# Conditionals
{{- if .Values.ingress.enabled }}
# ... ingress config
{{- end }}

# Loops
{{- range .Values.hosts }}
- host: {{ . }}
{{- end }}

# Default values
{{ .Values.name | default "myapp" }}

# String manipulation
{{ .Values.name | upper }}
{{ .Values.name | quote }}

# Include templates
{{- include "myapp.labels" . | nindent 4 }}

# toYaml
{{- toYaml .Values.resources | nindent 12 }}
```

**Test and Package**:

```bash
# Lint chart
helm lint myapp-chart/

# Dry run
helm install --dry-run --debug my-release myapp-chart/

# Template locally
helm template my-release myapp-chart/

# Package chart
helm package myapp-chart/

# Install
helm install my-release myapp-chart/ \
  --set image.tag=2.0.0
```

**Exercise**

- Create Helm chart for your application
- Add ConfigMap and Secret templates
- Implement conditional Ingress
- Test with different values files

### Day 48: GitOps with ArgoCD

**Theory (1 hour)**

- GitOps principles
- ArgoCD architecture
- Continuous deployment
- Sync strategies
- Multi-environment management

**Practice (1-2 hours)**

**Install ArgoCD**:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

**Create Application**:

```yaml
# application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-username/myapp-k8s
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**Directory Structure**:

```
myapp-k8s/
├── manifests/
│   ├── base/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── kustomization.yaml
│   ├── overlays/
│   │   ├── development/
│   │   │   ├── kustomization.yaml
│   │   │   └── patches.yaml
│   │   └── production/
│   │       ├── kustomization.yaml
│   │       └── patches.yaml
```

**Exercise**

- Install ArgoCD
- Create Git repository with manifests
- Deploy application via ArgoCD
- Test automated sync

### Day 49: Kustomize

**Theory (1 hour)**

- Kustomize basics
- Base and overlays
- Patches and transformers
- ConfigMap/Secret generators
- Kustomize vs Helm

**Practice (1-2 hours)**

**Base Configuration**:

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml

commonLabels:
  app: myapp
```

**Development Overlay**:

```yaml
# overlays/development/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namePrefix: dev-

replicas:
  - name: myapp
    count: 1

images:
  - name: myapp
    newTag: latest

configMapGenerator:
  - name: app-config
    literals:
      - APP_ENV=development
      - LOG_LEVEL=debug
```

**Production Overlay**:

```yaml
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namePrefix: prod-

replicas:
  - name: myapp
    count: 3

images:
  - name: myapp
    newTag: v1.2.3

configMapGenerator:
  - name: app-config
    literals:
      - APP_ENV=production
      - LOG_LEVEL=info

patchesStrategicMerge:
  - resources-patch.yaml
```

**Patch Example**:

```yaml
# resources-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
        - name: myapp
          resources:
            limits:
              cpu: 1000m
              memory: 1Gi
            requests:
              cpu: 500m
              memory: 512Mi
```

**Build and Apply**:

```bash
# Build dev
kubectl kustomize overlays/development/

# Apply dev
kubectl apply -k overlays/development/

# Apply prod
kubectl apply -k overlays/production/
```

**Exercise**

- Set up base configuration
- Create dev and prod overlays
- Use configMapGenerator
- Apply patches for different environments

### Day 50-51: Weekend Project 7 - Complete CI/CD Pipeline

**Project: GitOps-Driven Microservices Platform**

Build a complete CI/CD pipeline using GitOps principles for a microservices application.

**Application**: Social Media Platform

- User Service
- Post Service
- Comment Service
- Notification Service
- Media Service (Image upload/processing)
- API Gateway

**Requirements**:

**Source Control**:

- Application code repository
- Infrastructure repository (K8s manifests)
- Helm charts repository

**CI Pipeline** (GitHub Actions):

- Run tests
- Build Docker images
- Push to registry
- Security scanning
- Update manifest repo

**CD Pipeline** (ArgoCD):

- Monitor manifest repository
- Auto-sync to cluster
- Health checks
- Rollback on failure

**Environments**:

- Development (auto-deploy on commit)
- Staging (auto-deploy on PR merge)
- Production (manual approval)

**Deployment Strategy**:

- Canary deployments for production
- Blue-green for staging
- Direct deploy for development

**Deliverables**:

- Complete microservices application
- CI/CD pipeline configuration
- Helm charts for all services
- ArgoCD application manifests
- Environment-specific overlays
- Deployment documentation
- Rollback procedures
- Performance metrics

---

## WEEK 10-11: Production Operations

### Day 52: Disaster Recovery and Backups

**Theory (1 hour)**

- Backup strategies
- etcd backups
- Velero for cluster backups
- Database backup strategies
- Recovery testing

**Practice (1-2 hours)**

**Install Velero**:

```bash
# Download
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz

# Install CLI
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# Install in cluster (with MinIO for testing)
velero install \
    --provider aws \
    --plugins velero/velero-plugin-for-aws:v1.8.0 \
    --bucket velero \
    --secret-file ./credentials-velero \
    --use-volume-snapshots=false \
    --backup-location-config region=minio,s3ForcePathStyle="true",s3Url=http://minio.velero.svc:9000
```

**Create Backup**:

```bash
# Backup entire namespace
velero backup create myapp-backup --include-namespaces production

# Backup specific resources
velero backup create app-backup \
  --include-resources deployments,services,configmaps \
  --selector app=myapp

# Schedule automatic backups
velero schedule create daily-backup --schedule="0 2 * * *"
```

**Restore**:

```bash
# List backups
velero backup get

# Restore
velero restore create --from-backup myapp-backup

# Restore to different namespace
velero restore create --from-backup myapp-backup \
  --namespace-mappings production:production-restore
```

**Database Backup CronJob**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 */6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:15
              command:
                - /bin/bash
                - -c
                - |
                  BACKUP_FILE="/backup/db-$(date +%Y%m%d-%H%M%S).sql.gz"
                  pg_dump $DATABASE_URL | gzip > $BACKUP_FILE
                  # Upload to S3
                  aws s3 cp $BACKUP_FILE s3://my-backups/postgres/
              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: db-secret
                      key: url
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-volume
              emptyDir: {}
```

**Exercise**

- Install Velero
- Create manual backup
- Delete resources and restore
- Set up automated backup schedule

### Day 53: Cluster Upgrades

**Theory (1 hour)**

- Kubernetes version support policy
- Upgrade strategies
- Component upgrade order
- Testing upgrades
- Rollback procedures

**Practice (1-2 hours)**

**Check Current Version**:

```bash
kubectl version
kubectl get nodes -o wide
```

**Upgrade Plan** (Managed clusters):

```bash
# For managed Kubernetes (EKS, GKE, AKS)
# Follow cloud provider's upgrade process

# For kubeadm clusters
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply v1.28.0
```

**Node Upgrade Process**:

```bash
# Drain node
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# Upgrade node components
ssh node-1
sudo apt-get update
sudo apt-get install -y kubelet=1.28.0-00 kubectl=1.28.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon node
kubectl uncordon node-1
```

**Testing After Upgrade**:

```bash
# Check cluster health
kubectl get nodes
kubectl get pods --all-namespaces
kubectl get componentstatuses

# Test application
kubectl run test-pod --image=nginx --restart=Never
kubectl get pod test-pod
kubectl delete pod test-pod
```

**Exercise**

- Document current cluster version
- Plan upgrade path
- Test upgrade in dev environment
- Create upgrade checklist

### Day 54: Troubleshooting

**Theory (1 hour)**

- Common issues and solutions
- Debugging techniques
- Log analysis
- Performance debugging
- Network troubleshooting

**Practice (1-2 hours)**

**Pod Issues**:

```bash
# Pod not starting
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Previous container logs

# CrashLoopBackOff
kubectl describe pod <pod-name>  # Check events
kubectl logs <pod-name> --previous

# ImagePullBackOff
kubectl describe pod <pod-name>  # Check image and pull secrets

# Pending pods
kubectl describe pod <pod-name>  # Check resource constraints
kubectl get events --sort-by=.metadata.creationTimestamp
```

**Service Issues**:

```bash
# Service not accessible
kubectl get svc
kubectl describe svc <service-name>
kubectl get endpoints <service-name>  # Check if pods are registered

# Test service
kubectl run test --image=busybox -it --rm -- wget -qO- http://service-name:80
```

**Network Debugging**:

```bash
# Deploy debug pod
kubectl run netshoot --rm -it --image=nicolaka/netshoot -- bash

# Inside pod
nslookup kubernetes.default
ping <pod-ip>
curl http://service-name
traceroute service-name
```

**Performance Issues**:

```bash
# Check resource usage
kubectl top nodes
kubectl top pods
kubectl top pods --containers

# Check for resource constraints
kubectl describe node <node-name>

# Analyze events
kubectl get events --all-namespaces --sort-by='.lastTimestamp'
```

**PersistentVolume Issues**:

```bash
# Check PVC status
kubectl get pvc
kubectl describe pvc <pvc-name>

# Check PV
kubectl get pv
kubectl describe pv <pv-name>
```

**Exercise**

- Intentionally break different components
- Practice debugging each scenario
- Document troubleshooting steps

### Day 55: Chaos Engineering

**Theory (1 hour)**

- Chaos engineering principles
- Chaos Mesh
- Testing scenarios
- Observing system behavior
- Building resilience

**Practice (1-2 hours)**

**Install Chaos Mesh**:

```bash
# Add repo
helm repo add chaos-mesh https://charts.chaos-mesh.org

# Install
kubectl create ns chaos-testing
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-testing
```

**Pod Chaos Experiments**:

```yaml
# Pod kill experiment
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  scheduler:
    cron: "@every 2m"
```

**Network Chaos**:

```yaml
# Network delay
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  delay:
    latency: "100ms"
    correlation: "100"
    jitter: "0ms"
  duration: "5m"
```

**Stress Testing**:

```yaml
# CPU stress
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: cpu-stress
spec:
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  stressors:
    cpu:
      workers: 4
      load: 80
  duration: "2m"
```

**Exercise**

- Install Chaos Mesh
- Run pod kill experiments
- Test network latency impact
- Verify application resilience

### Day 56-57: Multi-Cluster Management

**Theory (1 hour each day)**

- Federation concepts
- Multi-cluster service mesh
- Cross-cluster communication
- Disaster recovery across clusters
- Global load balancing

**Practice (2-3 hours each day)**

**Managing Multiple Clusters**:

```bash
# Add cluster contexts
kubectl config get-contexts

# Set context
kubectl config use-context cluster-1

# Merge kubeconfig
KUBECONFIG=~/.kube/config:~/cluster2-config kubectl config view --flatten > ~/.kube/merged-config
```

**kubectx for Easy Switching**:

```bash
# Install kubectx
brew install kubectx

# List contexts
kubectx

# Switch context
kubectx cluster-1
kubectx cluster-2

# Namespace switching
kubens production
```

**Multi-Cluster with Istio**:

```yaml
# Install Istio on both clusters with mesh configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-multi-cluster
spec:
  values:
    global:
      meshID: mesh1
      multiCluster:
        clusterName: cluster-1
      network: network1
```

**Exercise**

- Set up two clusters (minikube can run multiple)
- Configure kubectl to access both
- Deploy application to both clusters
- Test failover between clusters

### Day 58-59: Weekend Project 8 - Production-Ready Platform

**Final Capstone Project: Complete Production Platform**

Build an enterprise-grade platform demonstrating all learned concepts.

**Platform**: **Multi-Tenant SaaS Analytics Platform**

**Core Features**:

- Real-time data ingestion
- Stream processing
- Analytics dashboard
- API for data access
- Multi-tenancy with isolation

**Architecture**:

```
                        [Global Load Balancer]
                                |
                    +-----------+-----------+
                    v                       v
              [Cluster 1]             [Cluster 2]
                    |                       |
                [Istio Mesh]          [Istio Mesh]
                    |                       |
        +-----------+-----------+           |
        v           v           v           |
    [Ingestion] [Processing] [API]         |
        |           |           |           |
        v           v           v           v
    [Kafka]     [Spark]    [Backend]   [Mirror]
        |           |           |
        +-----------+-----------+
                    v
            [PostgreSQL + Redis]
```

**Technical Requirements**:

**Multi-Cluster Setup**:

- Primary cluster (production)
- Secondary cluster (DR/staging)
- Cross-cluster service mesh
- Global ingress

**Scalability**:

- HPA on all services
- VPA for stateful components
- Cluster autoscaling
- Handle 10k requests/sec

**High Availability**:

- No single point of failure
- Multi-AZ deployment
- Database replication
- 99.9% uptime target

**Security**:

- Network policies (zero-trust)
- RBAC for all components
- Pod security standards
- Secret management (Vault)
- TLS everywhere
- Security scanning in CI

**Monitoring & Observability**:

- Prometheus + Grafana
- Loki for logs
- Jaeger for tracing
- Custom dashboards
- Alerting rules
- SLA monitoring

**CI/CD**:

- GitOps with ArgoCD
- Automated testing
- Canary deployments
- Automated rollbacks
- Multi-environment pipeline

**Disaster Recovery**:

- Automated backups (Velero)
- Cross-cluster replication
- RTO < 15 minutes
- RPO < 5 minutes
- Tested failover procedures

**Operations**:

- Chaos engineering tests
- Load testing results
- Capacity planning
- Cost optimization
- Upgrade procedures
- Runbooks for incidents

**Deliverables**:

1. Complete working platform
2. Infrastructure as Code (all YAML)
3. Helm charts for all components
4. CI/CD pipeline configurations
5. Monitoring dashboards
6. Architecture documentation
7. Operational runbooks
8. Disaster recovery plan
9. Performance test results
10. Cost analysis report
11. Video demo (10-15 minutes)

---

## WEEK 12-13: Advanced Topics and Specializations

### Day 60: Custom Resource Definitions (CRDs)

**Theory (1 hour)**

- Extending Kubernetes
- CRD structure
- API versioning
- Validation schemas

**Practice (1-2 hours)**

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: applications.example.com
spec:
  group: example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                image:
                  type: string
  scope: Namespaced
  names:
    plural: applications
    singular: application
    kind: Application
    shortNames:
      - app
```

### Day 61-62: Kubernetes Operators

**Theory and Practice**

Build a custom operator using Operator SDK.

### Day 63: Service Mesh Deep Dive

Advanced Istio features: traffic management, security policies, observability.

### Day 64: Serverless on Kubernetes

Knative for serverless workloads.

### Day 65: AI/ML Workloads

Kubeflow for machine learning pipelines.

### Day 66-70: Choose Your Path

**Path A: Cloud-Native Development**

- Develop cloud-native applications
- Advanced microservices patterns
- Event-driven architectures

**Path B: Platform Engineering**

- Build internal developer platforms
- Self-service capabilities
- Platform as a Product

**Path C: Security Specialization**

- Advanced security patterns
- Policy-as-code (OPA)
- Security scanning and hardening

**Path D: Multi-Cloud/Hybrid**

- Multi-cloud strategies
- Hybrid cloud patterns
- Cloud provider specifics

---

## 🎓 Final Capstone

### Day 71-90: Grand Finale Project

**Build Your Dream Platform**

Choose one of:

1. **E-Commerce Platform** (Full-stack)
2. **IoT Data Platform** (Event streaming)
3. **Gaming Platform** (Real-time, high-traffic)
4. **Healthcare Platform** (Compliance, security)
5. **Your Own Idea**

**Must Include**:

- All concepts from the roadmap
- Production-grade quality
- Complete documentation
- Presentation-ready demo

---

## 📚 Resources

### Books

- "Kubernetes in Action" by Marko Lukša
- "Kubernetes Patterns" by Bilgin Ibryam
- "Production Kubernetes" by Josh Rosso
- "Cloud Native DevOps with Kubernetes" by O'Reilly

### Online Courses

- Kubernetes Certified Administrator (CKA)
- Kubernetes Certified Application Developer (CKAD)
- Kubernetes Certified Security Specialist (CKS)

### Practice Platforms

- Killercoda (interactive scenarios)
- Play with Kubernetes
- KodeKloud
- Linux Foundation Training

### Communities

- Kubernetes Slack
- CNCF Community
- Reddit r/kubernetes
- Stack Overflow

---

## 🎯 Success Metrics

### Week 1-2 ✅

- [ ] Can explain containers and Kubernetes
- [ ] Deployed first application
- [ ] Comfortable with kubectl basics

### Week 3-5 ✅

- [ ] Understand all core objects
- [ ] Can troubleshoot common issues
- [ ] Completed 2-3 projects

### Week 6-8 ✅

- [ ] Implemented auto-scaling
- [ ] Set up monitoring
- [ ] Production deployment experience

### Week 9-11 ✅

- [ ] GitOps pipeline running
- [ ] Disaster recovery tested
- [ ] Operations confidence

### Week 12-13 ✅

- [ ] Advanced topics explored
- [ ] Final project completed
- [ ] Ready for certification

---

## 🏆 Next Steps After 90 Days

1. **Get Certified**

   - CKA (Administrator)
   - CKAD (Developer)
   - CKS (Security)

2. **Contribute to Open Source**

   - Kubernetes project
   - CNCF projects
   - Create your own operators

3. **Deep Dive Into Specialization**

   - Choose your path (DevOps, SRE, Platform Engineering)
   - Master cloud platforms
   - Learn advanced patterns

4. **Share Knowledge**
   - Write blog posts
   - Create tutorials
   - Speak at meetups
   - Mentor others

---

## 💡 Tips for Success

1. **Consistency**: 2-3 hours daily is better than 10 hours once a week
2. **Hands-on**: Actually deploy everything, don't just read
3. **Document**: Keep notes and screenshots
4. **Break things**: Learn by intentionally breaking and fixing
5. **Join community**: Ask questions, help others
6. **Build projects**: Real projects > toy examples
7. **Stay curious**: Technology evolves, keep learning

---

**Good luck on your Kubernetes journey! 🚀**
