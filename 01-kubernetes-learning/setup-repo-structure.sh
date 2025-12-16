#!/bin/bash

# Kubernetes Learning Repository Setup Script
# This script creates the complete folder structure for the 90-day Kubernetes learning journey

echo "🚀 Setting up Kubernetes Learning Repository Structure..."
echo ""

# Create main directories
echo "📁 Creating main directories..."
mkdir -p notes
mkdir -p manifests/{basics,deployments,services,storage,networking,security,advanced}
mkdir -p helm-charts/my-charts
mkdir -p scripts/{setup,cleanup,utilities}
mkdir -p practice/exercises
mkdir -p resources/{cheatsheets,diagrams,references}

# Create weekly directories (13 weeks)
echo "📅 Creating weekly directories..."
for week in {01..13}; do
    mkdir -p "week-${week}"
    # Create day directories for each week (7 days)
    for day in {01..07}; do
        mkdir -p "week-${week}/day-${day}"
    done
done

# Create project directories
echo "🏗️  Creating project directories..."
mkdir -p projects/project-01-wordpress-blog/{manifests,docs,screenshots}
mkdir -p projects/project-02-todo-app/{frontend,backend,database,manifests,docs}
mkdir -p projects/project-03-stateful-blog/{manifests,scripts,docs}
mkdir -p projects/project-04-ecommerce-microservices/{services,manifests,docs}
mkdir -p projects/project-05-production-saas/{manifests,helm,docs}
mkdir -p projects/project-06-news-aggregator/{app,manifests,monitoring,docs}
mkdir -p projects/project-07-gitops-microservices/{apps,infrastructure,ci-cd,docs}
mkdir -p projects/project-08-final-capstone/{cluster-1,cluster-2,manifests,helm,monitoring,docs}

# Create note files (numbered for sequence)
echo "📝 Creating note files..."

# Week 1-2: Foundation (01-10)
touch notes/01-container-fundamentals.md
touch notes/02-kubernetes-architecture.md
touch notes/03-first-deployment.md
touch notes/04-pods-basics.md
touch notes/05-deployments-basics.md
touch notes/06-services-basics.md
touch notes/07-labels-and-selectors.md
touch notes/08-namespaces.md
touch notes/09-configmaps.md
touch notes/10-secrets.md

# Week 3-5: Core Concepts (11-30)
touch notes/11-persistent-volumes.md
touch notes/12-persistent-volume-claims.md
touch notes/13-statefulsets.md
touch notes/14-storage-classes.md
touch notes/15-init-containers.md
touch notes/16-multi-container-patterns.md
touch notes/17-kubernetes-networking.md
touch notes/18-ingress-controllers.md
touch notes/19-network-policies.md
touch notes/20-dns-service-discovery.md
touch notes/21-service-mesh-intro.md
touch notes/22-advanced-configmaps.md
touch notes/23-resource-management.md
touch notes/24-rbac.md
touch notes/25-security-contexts.md
touch notes/26-pod-security-standards.md
touch notes/27-jobs.md
touch notes/28-cronjobs.md
touch notes/29-daemonsets.md
touch notes/30-resource-quotas.md

# Week 6-8: Scaling & Performance (31-50)
touch notes/31-horizontal-pod-autoscaling.md
touch notes/32-vertical-pod-autoscaling.md
touch notes/33-cluster-autoscaling.md
touch notes/34-performance-optimization.md
touch notes/35-prometheus-monitoring.md
touch notes/36-grafana-dashboards.md
touch notes/37-logging-with-loki.md
touch notes/38-alerting.md
touch notes/39-advanced-deployment-strategies.md
touch notes/40-blue-green-deployments.md
touch notes/41-canary-deployments.md
touch notes/42-helm-introduction.md
touch notes/43-helm-charts.md
touch notes/44-helm-templating.md
touch notes/45-helm-hooks.md
touch notes/46-gitops-principles.md
touch notes/47-argocd.md
touch notes/48-kustomize.md
touch notes/49-ci-cd-pipelines.md
touch notes/50-github-actions.md

# Week 9-11: Production Operations (51-70)
touch notes/51-disaster-recovery.md
touch notes/52-velero-backups.md
touch notes/53-cluster-upgrades.md
touch notes/54-troubleshooting.md
touch notes/55-debugging-techniques.md
touch notes/56-chaos-engineering.md
touch notes/57-multi-cluster-management.md
touch notes/58-federation.md
touch notes/59-service-mesh-deep-dive.md
touch notes/60-istio-advanced.md
touch notes/61-observability.md
touch notes/62-distributed-tracing.md
touch notes/63-cost-optimization.md
touch notes/64-capacity-planning.md
touch notes/65-sre-practices.md
touch notes/66-incident-response.md
touch notes/67-runbooks.md
touch notes/68-compliance-security.md
touch notes/69-policy-as-code.md
touch notes/70-opa-gatekeeper.md

# Week 12-13: Advanced Topics (71-90)
touch notes/71-custom-resource-definitions.md
touch notes/72-operators.md
touch notes/73-operator-sdk.md
touch notes/74-serverless-knative.md
touch notes/75-ml-workloads-kubeflow.md
touch notes/76-edge-computing.md
touch notes/77-multi-tenancy.md
touch notes/78-platform-engineering.md
touch notes/79-developer-experience.md
touch notes/80-advanced-networking.md
touch notes/81-ebpf-cilium.md
touch notes/82-security-advanced.md
touch notes/83-zero-trust.md
touch notes/84-supply-chain-security.md
touch notes/85-image-scanning.md
touch notes/86-runtime-security.md
touch notes/87-cloud-native-patterns.md
touch notes/88-12-factor-apps.md
touch notes/89-best-practices.md
touch notes/90-certification-prep.md

# Create README files for key directories
echo "📋 Creating README files..."

# Projects README
cat > projects/README.md << 'EOF'
# Kubernetes Learning Projects

This directory contains all hands-on projects for the 90-day Kubernetes learning journey.

## Projects Overview

1. **Project 1**: WordPress Blog (Week 1-2)
2. **Project 2**: Todo Application (Week 2)
3. **Project 3**: Stateful Blog Platform (Week 3)
4. **Project 4**: E-Commerce Microservices (Week 4)
5. **Project 5**: Production SaaS Platform (Week 5)
6. **Project 6**: News Aggregator (Week 6-7)
7. **Project 7**: GitOps Microservices (Week 8-9)
8. **Project 8**: Final Capstone (Week 10-13)

Each project directory contains:
- Application code
- Kubernetes manifests
- Documentation
- Screenshots/demos
EOF

# Manifests README
cat > manifests/README.md << 'EOF'
# Kubernetes Manifests

Reusable Kubernetes YAML files organized by category.

## Structure

- `basics/` - Simple pod and deployment examples
- `deployments/` - Various deployment patterns
- `services/` - Service configurations
- `storage/` - PV, PVC, StorageClass examples
- `networking/` - Ingress, NetworkPolicy examples
- `security/` - RBAC, SecurityContext, Secrets
- `advanced/` - StatefulSets, DaemonSets, Jobs, CronJobs
EOF

# Helm Charts README
cat > helm-charts/README.md << 'EOF'
# Helm Charts

Custom Helm charts created during the learning journey.

## Charts

This directory will contain various Helm charts for different applications.
EOF

# Scripts README
cat > scripts/README.md << 'EOF'
# Utility Scripts

Helper scripts for Kubernetes operations.

## Categories

- `setup/` - Cluster setup and configuration scripts
- `cleanup/` - Resource cleanup utilities
- `utilities/` - General purpose utilities
EOF

# Resources README
cat > resources/README.md << 'EOF'
# Learning Resources

Additional resources and references.

## Contents

- `cheatsheets/` - Quick reference guides
- `diagrams/` - Architecture diagrams
- `references/` - Links to documentation and articles
EOF

# Practice README
cat > practice/README.md << 'EOF'
# Practice Exercises

Quick practice exercises and code snippets.

Use this directory for:
- Testing concepts
- Quick experiments
- Code snippets
- Practice exercises
EOF

# Create cheatsheet files
echo "📚 Creating cheatsheet templates..."
cat > resources/cheatsheets/kubectl-cheatsheet.md << 'EOF'
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
EOF

cat > resources/cheatsheets/yaml-syntax.md << 'EOF'
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
EOF

# Create .gitkeep files for empty directories that should be tracked
echo "🔖 Creating .gitkeep files..."
find . -type d -empty -exec touch {}/.gitkeep \;

# Create a simple .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "📄 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Kubernetes
*.swp
*.swo
*~
.DS_Store

# IDE
.vscode/
.idea/
*.iml

# Secrets (never commit)
*secret*.yaml
*-secret.yaml
secrets/

# Temporary files
tmp/
temp/
*.tmp

# Logs
*.log

# Environment files
.env
.env.local

# Kubeconfig (never commit)
kubeconfig
*.kubeconfig
config

# Helm
charts/*.tgz
.helm/

# Terraform
*.tfstate
*.tfstate.backup
.terraform/

# Build artifacts
target/
build/
dist/
EOF
fi

echo ""
echo "✅ Repository structure created successfully!"
echo ""
echo "📊 Structure Summary:"
echo "   - 13 weekly directories (with 7 days each)"
echo "   - 8 project directories"
echo "   - 90 note files (numbered sequentially)"
echo "   - Organized manifest directories"
echo "   - Helper scripts and resources"
echo ""
echo "🎯 Next Steps:"
echo "   1. Review the main README.md"
echo "   2. Start with week-01/day-01"
echo "   3. Take notes in notes/01-container-fundamentals.md"
echo "   4. Build projects in the projects/ directory"
echo ""
echo "🚀 Happy Learning!"