.PHONY: help setup build deploy status logs clean restart port-forward all

# Default target
.DEFAULT_GOAL := help

# Variables
CLUSTER_NAME := todo-app-cluster
NAMESPACE := todo-app
BACKEND_IMAGE := todo-app-backend:latest
FRONTEND_IMAGE := todo-app-frontend:latest

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(GREEN)Todo App Kubernetes Management$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Build

setup: ## Create KIND cluster with ingress controller
	@echo "$(GREEN)🚀 Setting up KIND cluster...$(NC)"
	@kind create cluster --config k8s/local/kind-config.yaml
	@echo "$(GREEN)🌐 Installing NGINX Ingress Controller...$(NC)"
	@kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	@echo "$(YELLOW)⏳ Waiting for ingress controller...$(NC)"
	@kubectl wait --namespace ingress-nginx \
		--for=condition=ready pod \
		--selector=app.kubernetes.io/component=controller \
		--timeout=90s
	@echo "$(GREEN)✅ KIND cluster ready!$(NC)"
	@echo "$(YELLOW)📝 Don't forget to add '127.0.0.1 todo.local' to /etc/hosts$(NC)"

build: ## Build and load Docker images into KIND
	@echo "$(GREEN)🏗️  Building backend image...$(NC)"
	@cd todo-app && docker build -t $(BACKEND_IMAGE) --target production . || (echo "$(RED)❌ Backend build failed$(NC)" && exit 1)
	@echo "$(GREEN)🏗️  Building frontend image...$(NC)"
	@cd todo-app-frontend && docker build -t $(FRONTEND_IMAGE) . || (echo "$(RED)❌ Frontend build failed$(NC)" && exit 1)
	@echo "$(GREEN)📥 Loading images into KIND cluster...$(NC)"
	@kind load docker-image $(BACKEND_IMAGE) --name $(CLUSTER_NAME)
	@kind load docker-image $(FRONTEND_IMAGE) --name $(CLUSTER_NAME)
	@echo "$(GREEN)✅ Images built and loaded!$(NC)"

rebuild: ## Rebuild and reload images (useful for code changes)
	@echo "$(GREEN)🔄 Rebuilding images...$(NC)"
	@$(MAKE) build

##@ Deployment

deploy: ## Deploy all resources to Kubernetes
	@echo "$(GREEN)🚀 Deploying todo-app...$(NC)"
	@kubectl apply -f k8s/base/namespace.yaml
	@echo "$(GREEN)🗄️  Deploying database...$(NC)"
	@kubectl apply -f k8s/base/database/
	@echo "$(GREEN)🔧 Deploying backend...$(NC)"
	@kubectl apply -f k8s/base/backend/
	@echo "$(GREEN)🎨 Deploying frontend...$(NC)"
	@kubectl apply -f k8s/base/frontend/
	@echo "$(GREEN)🌐 Setting up ingress...$(NC)"
	@kubectl apply -f k8s/base/ingress.yaml
	@echo "$(YELLOW)⏳ Waiting for deployments...$(NC)"
	@kubectl wait --for=condition=available --timeout=300s \
		deployment/backend deployment/frontend -n $(NAMESPACE) 2>/dev/null || echo "$(YELLOW)⚠️  Deployments still starting...$(NC)"
	@echo "$(GREEN)✅ Deployment complete!$(NC)"
	@echo ""
	@echo "$(GREEN)🌍 Access your app at: http://todo.local$(NC)"
	@echo "$(YELLOW)   (Make sure '127.0.0.1 todo.local' is in /etc/hosts)$(NC)"

redeploy: rebuild ## Rebuild images and redeploy (full update)
	@echo "$(GREEN)🔄 Redeploying with new images...$(NC)"
	@kubectl rollout restart deployment/backend -n $(NAMESPACE)
	@kubectl rollout restart deployment/frontend -n $(NAMESPACE)
	@echo "$(GREEN)✅ Redeployment triggered!$(NC)"
	@$(MAKE) status

##@ Management

status: ## Check status of all resources
	@echo "$(GREEN)📊 Todo App Status$(NC)"
	@echo "=================="
	@echo ""
	@echo "$(YELLOW)Pods:$(NC)"
	@kubectl get pods -n $(NAMESPACE) 2>/dev/null || echo "$(RED)No pods found$(NC)"
	@echo ""
	@echo "$(YELLOW)Services:$(NC)"
	@kubectl get svc -n $(NAMESPACE) 2>/dev/null || echo "$(RED)No services found$(NC)"
	@echo ""
	@echo "$(YELLOW)Ingress:$(NC)"
	@kubectl get ingress -n $(NAMESPACE) 2>/dev/null || echo "$(RED)No ingress found$(NC)"

logs-backend: ## View backend logs
	@kubectl logs -f -l app=backend -n $(NAMESPACE)

logs-frontend: ## View frontend logs
	@kubectl logs -f -l app=frontend -n $(NAMESPACE)

logs-db: ## View database logs
	@kubectl logs -f -l app=postgres -n $(NAMESPACE)

logs: ## View all logs (opens in separate terminals - requires tmux)
	@echo "$(YELLOW)Opening logs in tmux...$(NC)"
	@tmux new-session -d -s todo-logs \; \
		send-keys 'kubectl logs -f -l app=backend -n $(NAMESPACE)' C-m \; \
		split-window -h \; \
		send-keys 'kubectl logs -f -l app=frontend -n $(NAMESPACE)' C-m \; \
		split-window -v \; \
		send-keys 'kubectl logs -f -l app=postgres -n $(NAMESPACE)' C-m \; \
		select-layout tiled \; \
		attach-session -t todo-logs

restart-backend: ## Restart backend deployment
	@kubectl rollout restart deployment/backend -n $(NAMESPACE)
	@echo "$(GREEN)✅ Backend restarted$(NC)"

restart-frontend: ## Restart frontend deployment
	@kubectl rollout restart deployment/frontend -n $(NAMESPACE)
	@echo "$(GREEN)✅ Frontend restarted$(NC)"

restart: ## Restart all deployments
	@kubectl rollout restart deployment/backend deployment/frontend -n $(NAMESPACE)
	@echo "$(GREEN)✅ All deployments restarted$(NC)"

##@ Port Forwarding

port-forward-backend: ## Port forward backend to localhost:8000
	@echo "$(GREEN)🔌 Port forwarding backend to localhost:8000$(NC)"
	@kubectl port-forward svc/backend 8000:8000 -n $(NAMESPACE)

port-forward-frontend: ## Port forward frontend to localhost:3000
	@echo "$(GREEN)🔌 Port forwarding frontend to localhost:3000$(NC)"
	@kubectl port-forward svc/frontend 3000:3000 -n $(NAMESPACE)

port-forward-db: ## Port forward database to localhost:5432
	@echo "$(GREEN)🔌 Port forwarding database to localhost:5432$(NC)"
	@kubectl port-forward svc/postgres 5432:5432 -n $(NAMESPACE)

##@ Utilities

hosts: ## Add todo.local to /etc/hosts
	@echo "127.0.0.1 todo.local" | sudo tee -a /etc/hosts
	@echo "$(GREEN)✅ Added todo.local to /etc/hosts$(NC)"

describe-backend: ## Describe backend pods
	@kubectl describe pods -l app=backend -n $(NAMESPACE)

describe-frontend: ## Describe frontend pods
	@kubectl describe pods -l app=frontend -n $(NAMESPACE)

exec-backend: ## Exec into backend pod
	@kubectl exec -it $$(kubectl get pod -l app=backend -n $(NAMESPACE) -o jsonpath='{.items[0].metadata.name}') -n $(NAMESPACE) -- /bin/sh

exec-frontend: ## Exec into frontend pod
	@kubectl exec -it $$(kubectl get pod -l app=frontend -n $(NAMESPACE) -o jsonpath='{.items[0].metadata.name}') -n $(NAMESPACE) -- /bin/sh

exec-db: ## Exec into database pod
	@kubectl exec -it $$(kubectl get pod -l app=postgres -n $(NAMESPACE) -o jsonpath='{.items[0].metadata.name}') -n $(NAMESPACE) -- psql -U postgres -d todo_app

##@ Cleanup

clean: ## Delete all resources (keeps cluster)
	@echo "$(YELLOW)🗑️  Deleting resources...$(NC)"
	@kubectl delete namespace $(NAMESPACE) --ignore-not-found=true
	@echo "$(GREEN)✅ Resources deleted$(NC)"

destroy: ## Destroy KIND cluster completely
	@echo "$(RED)🗑️  Destroying KIND cluster...$(NC)"
	@kind delete cluster --name $(CLUSTER_NAME)
	@echo "$(GREEN)✅ Cluster destroyed$(NC)"

reset: destroy setup ## Complete reset: destroy and recreate cluster
	@echo "$(GREEN)✅ Cluster reset complete$(NC)"

##@ Quick Commands

all: setup build deploy hosts ## Complete setup: cluster + build + deploy + hosts
	@echo ""
	@echo "$(GREEN)🎉 Everything is ready!$(NC)"
	@echo "$(GREEN)🌍 Visit: http://todo.local$(NC)"
	@$(MAKE) status

dev: ## Quick deploy for development (assumes cluster exists)
	@$(MAKE) rebuild
	@$(MAKE) redeploy
	@$(MAKE) status

check: ## Quick health check
	@echo "$(GREEN)🏥 Health Check$(NC)"
	@echo "Backend:  $$(curl -s http://todo.local/api/health || echo '$(RED)Failed$(NC)')"
	@echo "Frontend: $$(curl -s http://todo.local/api/health || echo '$(RED)Failed$(NC)')"

open: ## Open todo.local in browser
	@xdg-open http://todo.local 2>/dev/null || open http://todo.local 2>/dev/null || echo "$(YELLOW)Please open http://todo.local in your browser$(NC)"