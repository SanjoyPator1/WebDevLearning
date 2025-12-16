# Kubernetes Learning Journey 🚀

A comprehensive 90-day roadmap to master Kubernetes from beginner to advanced level.

## 📚 Learning Structure

This repository follows a structured 90-day learning plan divided into 13 weeks, with hands-on projects and detailed notes.

### Learning Phases

| Phase                             | Duration   | Focus Area                               | Status         |
| --------------------------------- | ---------- | ---------------------------------------- | -------------- |
| **Phase 1: Foundation**           | Week 1-2   | Container fundamentals & K8s basics      | 🔄 In Progress |
| **Phase 2: Core Concepts**        | Week 3-5   | Kubernetes objects & operations          | ⏳ Pending     |
| **Phase 3: Advanced Deployments** | Week 6-8   | Scaling, networking & storage            | ⏳ Pending     |
| **Phase 4: Production Readiness** | Week 9-11  | GitOps, monitoring & operations          | ⏳ Pending     |
| **Phase 5: Advanced Topics**      | Week 12-13 | Service mesh, operators & specialization | ⏳ Pending     |

## 📁 Repository Structure

```
kubernetes/
├── README.md                      # This file
├── .gitignore
│
├── notes/                         # Detailed learning notes (numbered)
│   ├── 01-container-fundamentals.md
│   ├── 02-kubernetes-architecture.md
│   ├── 03-pods-and-deployments.md
│   └── ...
│
├── week-01/                       # Weekly organized learning
│   ├── day-01/
│   ├── day-02/
│   └── ...
│
├── week-02/
├── week-03/
│   └── ... (up to week-13)
│
├── projects/                      # Hands-on projects
│   ├── project-01-wordpress-blog/
│   ├── project-02-todo-app/
│   ├── project-03-stateful-blog/
│   ├── project-04-ecommerce-microservices/
│   ├── project-05-production-saas/
│   ├── project-06-news-aggregator/
│   ├── project-07-gitops-microservices/
│   └── project-08-final-capstone/
│
├── manifests/                     # Kubernetes YAML files organized by topic
│   ├── basics/
│   ├── deployments/
│   ├── services/
│   ├── storage/
│   ├── networking/
│   ├── security/
│   └── advanced/
│
├── helm-charts/                   # Custom Helm charts
│   └── my-charts/
│
├── scripts/                       # Utility scripts
│   ├── setup/
│   ├── cleanup/
│   └── utilities/
│
├── practice/                      # Quick practice exercises
│   └── exercises/
│
└── resources/                     # Additional resources
    ├── cheatsheets/
    ├── diagrams/
    └── references/
```

## 🎯 Learning Objectives

### Week 1-2: Foundation ✅

- [ ] Understand containers and Docker
- [ ] Learn Kubernetes architecture
- [ ] Deploy first application
- [ ] Complete Project 1: WordPress Blog

### Week 3-5: Core Concepts

- [ ] Master Pods, Deployments, Services
- [ ] Work with ConfigMaps and Secrets
- [ ] Understand Storage (PV/PVC)
- [ ] Complete Projects 2-3

### Week 6-8: Advanced Deployments

- [ ] Implement auto-scaling (HPA/VPA)
- [ ] Set up monitoring with Prometheus
- [ ] Configure Ingress and networking
- [ ] Complete Projects 4-5

### Week 9-11: Production Readiness

- [ ] Implement GitOps with ArgoCD
- [ ] Master Helm templating
- [ ] Set up disaster recovery
- [ ] Complete Projects 6-7

### Week 12-13: Advanced Topics

- [ ] Explore CRDs and Operators
- [ ] Service mesh (Istio)
- [ ] Specialization path
- [ ] Complete Final Capstone

## 🚀 Projects

### Major Projects (8 Total)

1. **Project 1**: Multi-Container WordPress Blog (Week 1-2)

   - Basic pod and service creation
   - MySQL + WordPress deployment

2. **Project 2**: Full-Stack Todo Application (Week 2)

   - React frontend, FastAPI backend, PostgreSQL
   - ConfigMaps and Secrets

3. **Project 3**: Stateful Blog Platform (Week 3)

   - StatefulSets with MySQL replication
   - Persistent storage
   - Automated backups

4. **Project 4**: E-Commerce Microservices (Week 4)

   - Multiple microservices
   - Network policies
   - Service mesh integration

5. **Project 5**: Production-Grade SaaS Platform (Week 5)

   - Multi-tenant architecture
   - Complete security implementation
   - RBAC and resource management

6. **Project 6**: Auto-Scaling News Aggregator (Week 6-7)

   - HPA and VPA implementation
   - Performance optimization
   - Monitoring dashboards

7. **Project 7**: GitOps-Driven Microservices (Week 8-9)

   - Complete CI/CD pipeline
   - ArgoCD deployment
   - Multi-environment setup

8. **Project 8**: Final Capstone - Production Platform (Week 10-13)
   - Multi-cluster setup
   - Complete observability
   - Disaster recovery

## 📝 Notes Organization

Notes are numbered sequentially for easy navigation:

- `01-10`: Container fundamentals and K8s basics
- `11-20`: Core Kubernetes objects
- `21-30`: Storage and networking
- `31-40`: Security and configuration
- `41-50`: Scaling and performance
- `51-60`: GitOps and Helm
- `61-70`: Production operations
- `71-80`: Advanced topics

## 🛠️ Tools & Technologies

### Required Tools

- Docker
- kubectl
- minikube / kind / Docker Desktop
- Helm
- Git

### Monitoring & Operations

- Prometheus
- Grafana
- ArgoCD
- Velero
- Istio

### Languages & Frameworks

- Python (FastAPI)
- YAML
- Bash scripting

## 📖 How to Use This Repository

1. **Follow the Roadmap**: Start with Week 1, Day 1
2. **Take Notes**: Add your learnings to the numbered markdown files in `notes/`
3. **Practice Daily**: Complete exercises in the respective week folders
4. **Build Projects**: Implement each project in the `projects/` folder
5. **Organize Manifests**: Keep reusable YAML files in `manifests/`
6. **Track Progress**: Update this README with your progress

## 📅 Daily Routine

1. **Theory** (30-45 mins): Read and understand concepts
2. **Practice** (1-1.5 hours): Hands-on with kubectl and YAML
3. **Notes** (15-30 mins): Document learnings
4. **Review** (15 mins): Review previous day's work

## 🎓 Resources

### Official Documentation

- [Kubernetes Docs](https://kubernetes.io/docs/)
- [Docker Docs](https://docs.docker.com/)
- [Helm Docs](https://helm.sh/docs/)

### Practice Platforms

- [Killercoda](https://killercoda.com/)
- [Play with Kubernetes](https://labs.play-with-k8s.com/)
- [KodeKloud](https://kodekloud.com/)

### Certifications

- CKA (Certified Kubernetes Administrator)
- CKAD (Certified Kubernetes Application Developer)
- CKS (Certified Kubernetes Security Specialist)

## 📊 Progress Tracking

### Week 1

- [ ] Day 1: Container fundamentals
- [ ] Day 2: Docker deep dive
- [ ] Day 3: Building images
- [ ] Day 4: Kubernetes introduction
- [ ] Day 5: First deployment
- [ ] Day 6-7: Project 1

### Week 2

- [ ] Day 8: Deployments
- [ ] Day 9: Services
- [ ] Day 10: Labels and selectors
- [ ] Day 11: Namespaces
- [ ] Day 12: ConfigMaps and Secrets
- [ ] Day 13-14: Project 2

_... (Continue for all 13 weeks)_

## 🏆 Milestones

- [ ] Week 2: First application deployed ✨
- [ ] Week 5: Core concepts mastered 💪
- [ ] Week 8: Auto-scaling implemented 🚀
- [ ] Week 11: GitOps pipeline running 🔄
- [ ] Week 13: Final capstone completed 🎉
- [ ] Certification exam scheduled 📜

---

## 📂 Folder Structure & Usage

### **1. `notes/` Folder (90 numbered markdown files)**

**Purpose:** Your learning notes - theory, concepts, references

```
notes/
├── 01-container-fundamentals.md     ← Day 1 theory ✅
├── 02-kubernetes-architecture.md    ← Day 4 theory ✅
├── 03-first-deployment.md           ← Day 5 theory (need to create)
├── 04-pods-basics.md                ← Later
├── 05-deployments-basics.md         ← Later
└── ... (up to 90)

```

**What goes here:**

- Theory summaries
- Architecture diagrams
- Command references
- Your understanding of concepts
- Links to resources

**When to use:**

- Create/update while studying theory
- Reference later when you forget something

---

### **2. `week-XX/day-XX/` Folders**

**Purpose:** Your actual work - practice files, YAML files, scripts you create during hands-on

```
week-01/
├── day-01/              ← Day 1 hands-on work
│   ├── nginx-test.sh    ← Script you write
│   ├── docker-commands.txt  ← Commands you tried
│   └── notes.txt        ← Quick observations
├── day-02/              ← Day 2 hands-on work
│   ├── Dockerfile       ← Dockerfile you create
│   ├── app.py           ← Python app
│   └── test-commands.sh
├── day-03/
├── day-04/              ← Day 4 hands-on work
│   ├── kind-config.yaml
│   ├── first-pod.yaml
│   └── kubectl-commands.txt
└── day-05/
    ├── deployment.yaml
    ├── service.yaml
    └── testing-notes.txt

```

**What goes here:**

- YAML files you create
- Scripts you write
- Application code for testing
- Quick notes during hands-on
- Screenshots of errors/successes

**When to use:**

- During hands-on practice EVERY day
- This is your "scratch pad" for each day

---

### **3. `projects/` Folder**

**Purpose:** Complete projects (weekend projects from roadmap)

```
projects/
├── project-01-wordpress-blog/        ← Week 1 weekend (Day 6-7)
│   ├── manifests/
│   │   ├── mysql-pod.yaml
│   │   ├── wordpress-pod.yaml
│   │   └── services.yaml
│   ├── docs/
│   │   ├── README.md
│   │   └── architecture.md
│   └── screenshots/
│       └── running-wordpress.png
│
├── project-02-todo-app/              ← Week 2 weekend
│   ├── frontend/
│   ├── backend/
│   ├── database/
│   └── manifests/
│
└── project-03-stateful-blog/        ← Week 3 weekend
    └── ...

```

**What goes here:**

- Complete project code
- All K8s manifests for the project
- Documentation (README, architecture)
- Screenshots/demos
- Everything related to that specific project

**When to use:**

- Weekend projects (Days 6-7 of each week)
- Or multi-day projects

---

### **4. `manifests/` Folder**

**Purpose:** Reusable, well-organized YAML templates

```
manifests/
├── basics/
│   ├── simple-pod.yaml           ← Generic pod template
│   ├── pod-with-volume.yaml
│   └── multi-container-pod.yaml
├── deployments/
│   ├── nginx-deployment.yaml
│   ├── python-app-deployment.yaml
│   └── rolling-update-deployment.yaml
├── services/
│   ├── clusterip-service.yaml
│   ├── nodeport-service.yaml
│   └── loadbalancer-service.yaml
└── storage/
    ├── pv-example.yaml
    └── pvc-example.yaml

```

**What goes here:**

- Clean, reusable YAML templates
- Well-commented examples
- Best practice implementations
- Things you'll reference later

**When to use:**

- After you've tested something in `week-XX/day-XX/`
- Move working examples here
- Clean them up and add comments
- Create your own library of templates

**Workflow:**

```
1. Practice in week-01/day-03/ → Create deployment.yaml (messy)
2. Test and fix
3. Once working → Copy to manifests/deployments/ (clean version)
4. Add comments and documentation
5. Now you have reusable template!

```

---

### **5. `practice/` Folder**

**Purpose:** Quick experiments, one-off tests, code snippets

```
practice/
└── exercises/
    ├── test-nginx.yaml         ← Quick test
    ├── experiment-volumes.yaml ← Testing something
    ├── debug-network.sh        ← Debug script
    └── random-tests/           ← Mess around here

```

**What goes here:**

- Quick tests
- Experiments
- "Let me try something" files
- Stuff that doesn't belong in projects or week folders

**When to use:**

- Quick experiments
- Testing concepts
- Debugging issues
- Throwaway code

---

### **6. `resources/` Folder**

**Purpose:** Reference materials, cheatsheets, diagrams

```
resources/
├── cheatsheets/
│   ├── kubectl-cheatsheet.md   ← Already created ✅
│   ├── yaml-syntax.md          ← Already created ✅
│   ├── docker-cheatsheet.md    ← You can add
│   └── helm-cheatsheet.md      ← Later
├── diagrams/
│   ├── k8s-architecture.png    ← Save diagrams here
│   ├── networking-flow.png
│   └── my-architecture.drawio  ← Your own diagrams
└── references/
    ├── useful-links.md         ← Bookmark collection
    └── troubleshooting.md      ← Common issues you solved

```

**What goes here:**

- Cheatsheets you create or find
- Architecture diagrams
- Links to useful resources
- Reference materials

**When to use:**

- Throughout your learning
- When you find something useful
- Create your own quick references

---

### **7. `scripts/` Folder**

**Purpose:** Automation and utility scripts

```
scripts/
├── setup/
│   ├── install-kubectl.sh      ← Installation scripts
│   ├── setup-kind.sh
│   └── configure-env.sh
├── cleanup/
│   ├── delete-all-pods.sh      ← Cleanup utilities
│   ├── prune-images.sh
│   └── reset-cluster.sh
└── utilities/
    ├── deploy-helper.sh         ← Helper scripts
    ├── logs-viewer.sh
    └── port-forward-all.sh

```

**What goes here:**

- Bash scripts for automation
- Setup scripts
- Cleanup scripts
- Utility scripts

**When to use:**

- When you find yourself repeating commands
- Create scripts to automate
- Build your own tooling

---

### **8. `helm-charts/` Folder**

**Purpose:** Custom Helm charts (later in Week 6-7)

```
helm-charts/
└── my-charts/
    └── fastapi-app/         ← Your custom chart (Week 6-7)
        ├── Chart.yaml
        ├── values.yaml
        └── templates/

```

**What goes here:**

- Custom Helm charts you create
- Only use in Week 6+ when you learn Helm

**When to use:**

- Week 6-7 onwards
- Don't worry about this for now

---

## 🤝 Contributing to My Learning

This is a personal learning repository, but I'm open to:

- Suggestions for improvement
- Additional resources
- Best practice recommendations
- Code reviews on projects

## 📫 Connect

- GitHub: [@sanjoypator1](https://github.com/SanjoyPator1)
- LinkedIn: [Sanjoy Pator](https://www.linkedin.com/in/sanjoy-pator-91a41a182/)
- Portfolio: [devlopea.com](https://www.devlopea.com/portfolio/664c69d16fa0291b35450281)

## 📜 License

This is a personal learning repository. All Kubernetes and related technologies are subject to their respective licenses.

---

**Last Updated**: Dec 2025
**Current Week**: Week 1  
**Current Status**: Learning container fundamentals 🔥

---

> "The journey of a thousand miles begins with a single step." - Start with Day 1! 🚀
