# 16 — Kubernetes: Running Containers at Scale, Declaratively

> Phase 6 · Infrastructure & delivery · Builds on: 15 (containers), 01 (LB/DNS), 02 (workers/replicas), 08/09 (draining)
> Playground: you already have a **KIND** cluster in `k8s/` — this topic makes you understand and extend it

---

## 1. Why this matters

You already have a working KIND setup in `k8s/` (namespace, deployments, ingress, scripts) — which
means you can *run* Kubernetes but maybe not yet *reason* about it. This topic closes that gap:
what each object actually does, why the whole thing is a declarative control loop, how health
probes and resource requests decide whether your app survives, and how it scales. Kubernetes is
the industry's default deployment substrate; being fluent here is table stakes for backend/platform roles.

The design goal from topic 15 pays off here: a compose service → Deployment, a compose network →
Service, a volume → PVC. You're generalizing what you already know.

---

## 2. Concepts in depth

### 2.1 The core idea — declarative + control loops
- You declare **desired state**; controllers continuously **reconcile** actual → desired. This one idea explains all of k8s
- Why this beats imperative `docker run` scripts: self-healing, rolling changes, drift correction
- The API-server-centric model: everything is an object in etcd; `kubectl apply` just posts objects; controllers watch and act
- Architecture: control plane (API server, etcd, scheduler, controller-manager) vs nodes (kubelet, kube-proxy, container runtime) — enough to reason about failures

### 2.2 Pods & workload controllers
- **Pod**: the smallest unit — one-or-more containers sharing network+storage; why usually one app container + optional sidecars
- **Deployment** (stateless apps — your todo-app & frontend): ReplicaSets, rolling updates, rollbacks, `revisionHistoryLimit`
- **StatefulSet** (stable identity + storage — databases, brokers): ordered, stable network ids, per-pod PVCs — and why you often DON'T self-host stateful things (use RDS/managed instead, topic 18)
- **DaemonSet** (one per node — log/metric agents from topic 14)
- **Job / CronJob** (batch + scheduled — the k8s answer to topic 08's scheduled jobs; the distributed-cron problem solved by the platform)
- Init containers & sidecars (e.g., migrations as an init container, a proxy sidecar); the sidecar-as-native (1.28+) awareness

### 2.3 Networking ⭐ (the part people find hardest)
- The k8s network model: every pod gets its own IP, all pods can reach all pods (flat) — CNI plugins implement it
- **Service**: stable virtual IP + DNS name in front of ephemeral pods (pods die and get new IPs — Service is the stable front). This IS topic 01's load balancing + topic 15's service discovery, generalized
- Service types: **ClusterIP** (internal), **NodePort**, **LoadBalancer** (cloud LB), **ExternalName**
- **kube-proxy** and how Service routing actually works (iptables/IPVS) — conceptual
- **Ingress** (you have one in `k8s/base/ingress.yaml`): L7 HTTP routing, host/path rules, TLS termination (topic 01!) — and the **Ingress Controller** (nginx/Traefik) that actually implements it
- **Gateway API** — the modern successor to Ingress; know it's the direction
- DNS in-cluster (CoreDNS): `service.namespace.svc.cluster.local` — the naming you'll use; NetworkPolicies for pod-to-pod firewalling (ties to topic 07 zero-trust)

### 2.4 Configuration & secrets
- **ConfigMap** (non-secret config) and **Secret** (base64, NOT encrypted at rest by default — the common misconception); enabling encryption-at-rest / external secret stores
- Injecting config: env vars vs mounted files; reload behavior
- **External Secrets Operator** / Sealed Secrets / Vault / cloud secret managers (topic 07/18) — how real clusters handle secrets safely
- The 12-factor config story (topic 15) landing in k8s

### 2.5 Storage
- Ephemeral vs persistent; **PersistentVolume / PersistentVolumeClaim / StorageClass** — dynamic provisioning
- Access modes (RWO/ROX/RWX) and why they constrain you
- The honest take: prefer managed stateful services (RDS, ElastiCache — topics 04/06/18) over self-hosting databases in k8s; when StatefulSets are genuinely right
- Your file-storage lesson pays off (topic 10): app pods stay stateless, files live in object storage, not PVCs

### 2.6 Health, resources & scheduling ⭐ (what keeps you up = what you configure here)
- **Probes** (this is where topic 01's health-checks become concrete):
  - **liveness** (restart if dead), **readiness** (remove from Service if not ready — protects rolling deploys), **startup** (slow-boot grace)
  - the classic outage: conflating liveness & readiness, or a liveness probe that restarts a busy-but-healthy pod
- **Resource requests & limits** (cgroups from topic 15, now scheduled): requests drive scheduling &
  QoS class (Guaranteed/Burstable/BestEffort); limits enforce ceilings; CPU throttling vs memory OOMKill (137)
- The scheduler: how requests + node capacity + affinity/anti-affinity/taints/tolerations place pods —
  including **GPU nodes** for topic 08's inference workers (nodeSelector/taints route GPU jobs to GPU nodes)
- Graceful shutdown in k8s: SIGTERM → `terminationGracePeriodSeconds` → SIGKILL; `preStop` hooks; connection draining (delivers on topics 08/09 draining), and readiness-gate-before-shutdown
- Disruptions: PodDisruptionBudgets so voluntary disruptions (node drains, upgrades) don't take you down

### 2.7 Scaling & self-healing
- **HorizontalPodAutoscaler**: scale replicas on CPU/memory or custom metrics (queue depth from topic 08!, via KEDA) — the cloud version of "add workers when the queue is deep"
- **KEDA** for event-driven autoscaling (scale on Kafka lag, SQS depth, etc. — ties topics 08/11) and scale-to-zero (topic 08's GPU cost control)
- VerticalPodAutoscaler & Cluster Autoscaler / Karpenter (nodes scale too) — awareness
- Self-healing: crash → restart, node dies → reschedule, rolling update with surge/unavailable controls & automatic rollback on failed readiness

### 2.8 Packaging & config management ⭐
- The problem: raw YAML doesn't scale across environments (dev/staging/prod duplication) — exactly what you'll feel extending `k8s/base`
- **Kustomize**: base + overlays, patches, no templating — k8s-native (your repo has a `base/` dir, so overlays are the natural next step)
- **Helm**: templated charts, values, releases, dependencies — the package manager; when Helm vs Kustomize (and using both)
- Chart/overlay structure for multi-env; secrets handling in each
- **Operators & CRDs**: extending k8s with your own controllers (the control-loop idea from §2.1 applied to your own domain); when you'd use/build one vs just deployments

### 2.9 Observability, security & operations
- Observability in-cluster (topic 14): Prometheus (ServiceMonitors), Grafana, Loki, Jaeger, OTel Collector as a DaemonSet/Deployment; `kubectl logs`, events, `describe` as first-line debugging
- **RBAC** (topic 07 in k8s): ServiceAccounts, Roles/ClusterRoles, RoleBindings — least privilege for workloads and humans
- Pod security: securityContext (non-root/read-only/cap-drop from topic 15 Lab 7), Pod Security Standards, NetworkPolicies, admission control (OPA Gatekeeper/Kyverno)
- **Service mesh** (topic 12): Istio/Linkerd landing in k8s — mTLS, traffic shifting, telemetry via sidecars; when it's worth it
- Multi-tenancy in k8s: namespaces + quotas + RBAC + NetworkPolicies (echoes the tenancy theme of 04/10)
- Debugging workflow: `kubectl describe`/`logs`/`events`/`exec`/`port-forward`, ephemeral debug containers, reading CrashLoopBackOff/ImagePullBackOff/OOMKilled

### 2.10 Managed Kubernetes & when NOT to use k8s
- Managed control planes (EKS/GKE/AKS) vs self-managed; what "managed" does and doesn't cover
- The honest cost/complexity conversation: k8s is powerful and heavy — when a PaaS (ECS/Fargate, Cloud Run, Fly, Render) or even a single box is the smarter call for a small team

---

## 3. Hands-on labs

> Work in `labs/16_kubernetes/` and by extending your existing `k8s/` dir on the KIND cluster.

**Lab 1 — Read your own cluster.**
Walk every object in `k8s/base` (namespace, deployments, service, ingress). For each, run
`kubectl explain` + `describe` and write, in your own words, what it does and what breaks without it.
Draw the request path from ingress → service → pod (topic 01 in k8s form).

**Lab 2 — Break and self-heal.**
`kubectl delete pod` on a running todo-app pod; watch the Deployment recreate it. `kubectl scale`
to 3 replicas; watch the Service load-balance. Cordon/drain a KIND node; watch rescheduling.

**Lab 3 — Probes done right (the outage-prevention lab).**
Add liveness/readiness/startup probes to the todo-app. Then misconfigure on purpose: a liveness
probe that fails under load → watch k8s restart healthy pods (the classic self-inflicted outage).
Fix the split between liveness and readiness. Add graceful shutdown (preStop + grace period) and
prove zero dropped requests during a rolling deploy (ties to topics 08/09).

**Lab 4 — Resources, QoS, and OOMKill.**
Set requests/limits; identify the QoS class. Push memory past the limit → observe OOMKilled (137).
Set CPU limits and watch throttling under load. Right-size using topic 14 metrics.

**Lab 5 — Config, secrets, migrations.**
Move config to a ConfigMap and secrets to a Secret (then note it's just base64 — enable a proper
external secret approach). Run Alembic migrations (topic 04) as an init container or a Job before rollout.

**Lab 6 — Autoscale on a real signal.**
HPA on CPU first. Then install KEDA and autoscale a worker Deployment (topic 08) on **queue depth**
/ Kafka **consumer lag** (topic 11) — the "add workers when backed up" rule, automated. Load it and watch pods scale (and scale to zero).

**Lab 7 — Kustomize overlays for multi-env.**
Refactor `k8s/base` into base + `overlays/{dev,prod}` with Kustomize (different replicas, resources,
config per env). Then package the same app as a Helm chart and compare the two approaches in `NOTES.md`.

**Lab 8 — Stateful + storage.**
Deploy Postgres as a StatefulSet with a PVC on KIND (to *understand* it) — then write down why in
production you'd use RDS instead (topic 18). Confirm app pods stay stateless with files in MinIO (topic 10).

**Lab 9 — Security hardening.**
Apply securityContext (non-root, read-only, cap-drop from topic 15), a restrictive NetworkPolicy
(frontend→api only, api→db only), RBAC ServiceAccounts with least privilege, and a Kyverno/Gatekeeper
policy that rejects privileged pods. Try to violate each and watch it get blocked.

**Lab 10 — Full-system deploy + debug drill.**
Deploy the whole stack (api, workers, frontend, redis, redpanda, observability from topic 14) to
KIND via your overlays. Then break something (bad image tag, failing probe, missing config) and
diagnose purely with `kubectl describe/logs/events`. Time yourself.

## 4. AWS mapping

| Local (KIND) concept | AWS equivalent | Notes |
|---|---|---|
| KIND cluster | **EKS** | Managed control plane; you manage/auto-manage nodes |
| Node management | Managed node groups / **Karpenter** | Autoscaling nodes, incl. GPU & spot |
| Service type LoadBalancer | **AWS Load Balancer Controller** → ALB/NLB | Topic 01's LBs, provisioned from k8s |
| Ingress | ALB Ingress / Gateway API | L7 routing + ACM TLS (topic 01) |
| PVC/StorageClass | **EBS/EFS CSI drivers** | Dynamic volumes |
| Secrets | **External Secrets Operator** → Secrets Manager/SSM | Topic 07/18 |
| ServiceAccount → cloud perms | **IRSA / EKS Pod Identity** | Pods assume IAM roles (topic 18) — the secure way |
| kube metrics | Managed Prometheus/Grafana, Container Insights | Topic 14 |
| GPU node pools | EKS GPU node groups | Topic 08 inference workers |

---

## 5. Mini-project — "The todo-app platform on Kubernetes"

Extend your `k8s/` into a real platform (KIND locally, EKS-ready), in `labs/16_kubernetes/`:

1. Deployments for api + frontend + workers, all with correct liveness/readiness/startup probes, resources, graceful shutdown, non-root/read-only securityContext
2. Migrations as a pre-deploy Job/init container; ConfigMap + Secret (external-secrets-ready) config
3. HPA on CPU **and** KEDA autoscaling workers on queue depth / consumer lag (topics 08/11); GPU nodeSelector for the inference worker
4. Kustomize base + dev/prod overlays (and a Helm chart variant); Ingress with TLS
5. NetworkPolicies + RBAC + a policy engine rejecting insecure pods; full observability stack (topic 14) deployed in-cluster
6. A rolling deploy that drops zero requests, and a documented `kubectl` debug runbook
7. **`K8S.md`**: object-by-object rationale, the compose→k8s mapping, scaling design, and the
   "when NOT to use k8s" honest note. (Pairs with your existing `k8s/README.md`.)

Done = you can deploy, scale, secure, autoscale, roll out, and debug the whole system on k8s, and explain every object.

---

## 6. Self-check — you're done when you can…

1. Explain the declarative control-loop model and why it beats imperative deploy scripts.
2. Explain Pod vs Deployment vs StatefulSet vs DaemonSet vs Job/CronJob and pick the right one for five workloads.
3. Explain how a Service gives stable access to ephemeral pods, and trace a request ingress→service→pod.
4. Explain liveness vs readiness vs startup probes and describe an outage caused by conflating them.
5. Explain requests vs limits, QoS classes, and the difference between CPU throttling and OOMKill.
6. Explain graceful shutdown in k8s (SIGTERM, grace period, preStop, readiness) and how it yields zero-downtime deploys.
7. Autoscale on a queue/lag signal and explain why that beats CPU-based scaling for workers.
8. Explain Kustomize vs Helm and when you'd use each.
9. Secure a workload: non-root/read-only, NetworkPolicy, RBAC, admission policy — and say what each blocks.
10. Make the honest call on when a team should NOT use Kubernetes.

---

## 7. Resources

- **kubernetes.io docs — Concepts section** — genuinely good; read Workloads, Services/Networking, Configuration, Scheduling
- **"Kubernetes Up & Running" (Burns, Beda, Hightower)** — the canonical intro book
- **"The Kubernetes Book" — Nigel Poulton** — pairs with his Docker book; very approachable
- **KEDA docs + "HPA/autoscaling" k8s docs** — event-driven autoscaling (Lab 6)
- **Kustomize docs + Helm docs** — packaging (§2.8)
- **learnk8s.io articles + "Kubernetes the Hard Way" (Kelsey Hightower)** — the "hard way" if you want to truly understand the control plane
- **EKS Best Practices Guide (AWS)** — after local, this is the production/EKS bridge (IRSA, networking, security)
- **killercoda / kube.academy interactive scenarios** — hands-on practice environments
