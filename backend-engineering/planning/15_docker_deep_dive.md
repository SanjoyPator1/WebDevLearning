# 15 — Docker Deep Dive: Containers From the Inside Out

> Phase 6 · Infrastructure & delivery · Builds on: everything you've been running in compose all along
> Playground: this topic makes your images production-grade; adds a local **registry**

---

## 1. Why this matters

You've used Docker since the todo-app — `docker-compose up`, a Dockerfile, the KIND setup. This
topic is about what's *underneath*: what a container actually is (not a VM), why your images are
600MB when they should be 80MB, why "works on my machine" still happens, and how images become a
security and supply-chain surface. Everything in topics 16–18 (k8s, CI/CD, cloud) assumes solid
container fundamentals — get them right here so the rest is smooth.

---

## 2. Concepts in depth

### 2.1 What a container actually is (demystify it)
- A container is **a process** with a restricted view — NOT a VM. No guest kernel; shares the host kernel
- The three Linux primitives it's built from:
  - **namespaces** (isolation of what a process can *see*: pid, net, mount, uts, ipc, user)
  - **cgroups** (limits on what it can *use*: CPU, memory, I/O — the thing that enforces your `cpus:`/`mem_limit:`)
  - **union filesystems** (overlayfs — layered, copy-on-write images)
- VM vs container: boundary, boot time, density, isolation strength — and when you actually want a VM (or a microVM like Firecracker) for stronger isolation
- The daemon landscape: Docker vs containerd vs the OCI standard; why "Docker" is really several pieces

### 2.2 Images & layers (why size and cache behavior are what they are)
- Images are stacked read-only **layers** + a writable container layer on top (copy-on-write)
- **Layer caching**: each Dockerfile instruction = a layer; the cache invalidates from the first
  changed instruction down — this dictates instruction ORDER (why you `COPY requirements.txt` and
  install deps BEFORE `COPY . .`, which your todo-app Dockerfile should do)
- Image digests vs tags; why `latest` is a trap; content-addressable storage
- Registries: how push/pull works, layer dedup, manifest & manifest lists (multi-arch)
- Reading `docker history` / `dive` to see where your megabytes went

### 2.3 Writing production Dockerfiles ⭐
- **Multi-stage builds**: a fat build stage (compilers, dev deps) → copy only artifacts into a slim
  runtime stage. The single biggest lever on image size & attack surface. (Your todo-app uses a
  `target: development` stage — extend this to a lean production target.)
- Base image choice: `python:3.x` vs `-slim` vs `alpine` (musl/wheels gotchas!) vs **distroless** vs
  scratch — the size/compatibility/security trade-off, with the Python-specific alpine warning
- Layer optimization: order by change frequency, combine RUN steps, `.dockerignore` (stop shipping `.git`, `.venv`, tests)
- Dependency install done right (uv/pip caching, `--no-cache-dir`, lockfiles — ties to your existing `uv export`)
- **The non-root rule**: create and run as a non-root user (container escape mitigation); `USER` directive
- Signals & PID 1: why your app must handle SIGTERM for graceful shutdown (ties to topics 08/09 draining), the zombie-reaping problem, `--init`/tini
- `EXPOSE`, `ENV`, `ARG`, build-time vs runtime config; healthchecks in the image
- `ENTRYPOINT` vs `CMD` and the exec-form vs shell-form footgun (signals again)
- Build reproducibility: pinned base digests, pinned deps; BuildKit features (cache mounts, secrets at build time — never bake secrets into layers!)

### 2.4 Container runtime & configuration
- Running as an immutable, stateless unit (topic 01's statelessness, now literal) — config via env/secrets, not baked in
- **12-factor app** principles applied to containers (config, logs to stdout, disposability, dev/prod parity)
- Resource limits (cgroups): CPU/memory requests & limits; the **OOMKill** (exit 137) you'll meet, and why an unbounded container is a bad neighbor (ties to topic 16 requests/limits)
- Filesystem: volumes vs bind mounts vs tmpfs; why container writes are ephemeral (topic 10 taught you to put files in object storage, not the container)
- Logging: stdout/stderr → the runtime's logging driver (feeds topic 14); never log to files inside the container

### 2.5 Networking (fills the gap under your compose files)
- Network namespaces → the **bridge** network Docker gives you; how containers get IPs
- **Embedded DNS**: service-name resolution in compose (why `db` resolves — this is topic 01's DNS as service discovery, and it's what k8s Services generalize)
- Port publishing vs internal-only; the difference between "exposed" and "published"
- Network drivers: bridge, host, none, overlay (multi-host) — one line each
- Inter-container communication and isolation via networks (your compose already uses `todo_network`)

### 2.6 Security & supply chain ⭐ (images are an attack surface)
- Minimize attack surface: smallest base, fewest packages, distroless/non-root, drop capabilities, read-only root filesystem
- **Vulnerability scanning**: Trivy / Grype / Docker Scout — scanning images for CVEs in base + deps (ties to topic 07 dependency hygiene); wiring it into CI (topic 17)
- **Supply-chain integrity**: image signing (cosign/sigstore), provenance/SBOM (Syft), pinning by digest — the "did I run the image I built?" problem
- Secrets: NEVER in image layers or env baked at build (they persist in history); use runtime secrets / BuildKit secret mounts; scanning for leaked secrets (gitleaks, topic 07)
- Runtime hardening: `--read-only`, `--cap-drop ALL`, seccomp/AppArmor profiles, no `--privileged`, user namespaces
- Rootless Docker and why it matters

### 2.7 Build & registry workflow (sets up CI/CD)
- Tagging strategy: semantic + git-sha tags, immutable tags (never re-push a tag), `latest` discipline
- **Multi-arch builds** (buildx): amd64 + arm64 (your Mac is arm64, most cloud is amd64 — the mismatch that bites) and QEMU emulation
- Local **registry** container; pushing/pulling; how this becomes ECR/GHCR later (topics 17/18)
- Build speed: layer cache reuse in CI, cache mounts, remote cache — why cold builds kill pipeline time

### 2.8 Compose in depth & its limits
- Compose as the local-dev orchestrator (you already use it well): profiles, depends_on + healthcheck conditions, env files, override files
- Where compose stops: multi-host, self-healing, autoscaling, rolling deploys — the exact gap that **Kubernetes** (topic 16) fills
- The mental bridge: a compose `service` → a k8s Deployment; a compose network → k8s Service DNS; a compose volume → a PVC — so topic 16 feels like a generalization, not a new world

---

## 3. Hands-on labs

> Code in `labs/15_docker_deep_dive/`, mostly hardening the todo-app & frontend images.

**Lab 1 — See the layers and shrink the image.**
Run `dive` / `docker history` on the todo-app image. Rewrite the Dockerfile as a **multi-stage
build** with a slim/distroless runtime target and a non-root user. Measure before/after size
(target: a fraction of the original). Verify it still runs and handles SIGTERM gracefully.

**Lab 2 — Prove the layer cache.**
Order instructions badly (COPY . . before installing deps) and time a rebuild after a code change.
Fix the order; time again. Add a proper `.dockerignore`. Quantify the build-time difference.

**Lab 3 — Namespaces & cgroups, hands-on.**
Run a container and inspect its namespaces (`lsns`, `/proc/<pid>/ns`) and cgroup limits from the
host. Set `--memory=128m` and run something that allocates more — watch the OOMKill (exit 137).
Set `--cpus=0.5` and watch throttling under load. Connect to topic 16's requests/limits.

**Lab 4 — Networking & DNS.**
Two containers on a user-defined network; resolve each other by name (embedded DNS). Then put them
on separate networks and prove they can't reach each other. Map it to topic 01's DNS-as-discovery
and preview topic 16's Service DNS.

**Lab 5 — Scan and sign (supply chain).**
Scan the todo-app image with Trivy; fix the fixable CVEs (bump base, remove packages). Generate an
SBOM with Syft. Sign the image with cosign and verify the signature. Document what each step defends against.

**Lab 6 — Multi-arch build.**
Build the image for amd64 + arm64 with buildx; push to a local registry. Explain the Mac-arm64 /
cloud-amd64 mismatch and how manifest lists solve it.

**Lab 7 — Harden the runtime.**
Run the todo-app container with `--read-only` root fs (+ tmpfs for what needs writing),
`--cap-drop ALL`, non-root user, no privileged. Fix what breaks. This is exactly the k8s
securityContext you'll write in topic 16.

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Local registry | **ECR** (Elastic Container Registry) | Private registry; lifecycle policies, scan-on-push |
| `docker run` a container | **ECS/Fargate** task, **EKS** pod | Topic 16/18 |
| Trivy/Scout scanning | ECR image scanning (basic/enhanced via Inspector) | CVE scanning in the registry |
| Image signing/provenance | ECR + cosign / AWS Signer | Supply-chain integrity |
| BuildKit/buildx in CI | **CodeBuild** / GitHub Actions | Topic 17 |
| Multi-arch | ECR manifest lists | Graviton (arm64) cost savings are real |

---

## 5. Mini-project — "Production-grade images for the whole stack"

In `labs/15_docker_deep_dive/`:

1. Multi-stage, slim/distroless, non-root, SIGTERM-handling images for BOTH the todo-app and the Next.js frontend
2. `.dockerignore` + cache-optimal layer ordering; documented before/after size and build-time numbers
3. Trivy scan clean (or documented exceptions) + SBOM + cosign signature, wired so it's CI-ready (topic 17)
4. Multi-arch (amd64/arm64) images pushed to a local registry with a sane tagging strategy
5. Runtime-hardened (`read-only`, cap-drop, non-root) — the exact settings that become topic 16's securityContext
6. **`CONTAINERS.md`**: the image-build philosophy, size/security decisions, the supply-chain steps,
   and the compose→k8s mental bridge. (Your existing docker-compose stays as the dev experience.)

Done = tiny, non-root, scanned, signed images that run read-only and shut down gracefully.

---

## 6. Self-check — you're done when you can…

1. Explain what a container is in terms of namespaces, cgroups, and union filesystems — and how it differs from a VM.
2. Explain layer caching and reorder a Dockerfile for optimal cache behavior, justifying each move.
3. Explain multi-stage builds and how they cut both size and attack surface.
4. Choose a base image (slim vs alpine vs distroless) for a Python service and defend it, including the alpine gotcha.
5. Explain why containers run as non-root and read-only, and what container escape those mitigate.
6. Explain PID 1/SIGTERM handling and why it matters for graceful shutdown (link to topics 08/09).
7. Explain the OOMKill and CPU throttling in terms of cgroups, and how they map to k8s limits.
8. Explain image scanning, SBOMs, and signing — the three supply-chain concerns and their tools.
9. Explain container DNS/service discovery and how it previews k8s Services.
10. Explain exactly where compose stops and Kubernetes begins.

---

## 7. Resources

- **Docker docs — "Best practices for building images" + BuildKit docs** — the official §2.3 reference
- **"Docker Deep Dive" — Nigel Poulton** — the clearest end-to-end containers book
- **Julia Evans — "How containers work" zine + blog** ([jvns.ca](https://jvns.ca)) — namespaces/cgroups intuition, beautifully
- **Google distroless repo + "Distroless" talks** — minimal, secure runtime images
- **Trivy, Syft/Grype, cosign/sigstore docs** — the supply-chain toolchain (§2.6)
- **redhat "Architecting Containers" series** — namespaces/cgroups from first principles
- **The Twelve-Factor App (12factor.net)** — the config/logs/disposability principles containers assume
