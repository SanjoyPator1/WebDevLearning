# 17 — CI/CD & Infrastructure as Code: Ship Safely, Repeatably, Automatically

> Phase 6 · Infrastructure & delivery · Builds on: 13 (tests), 15 (images), 16 (k8s deploy targets)
> Tools: GitHub Actions, Terraform, ArgoCD (all runnable locally / free tier)

---

## 1. Why this matters

Everything so far you've run by hand. Production means: a push triggers tests, builds a signed
image, and rolls it out — with the ability to roll back in seconds and to recreate the entire
infrastructure from code. Manual deploys and click-configured cloud consoles are how outages,
"works in staging", and un-reproducible environments happen.

CI/CD and Infrastructure as Code are what make the previous 16 topics *operable*: the test suite
(13) becomes a gate, the images (15) get built and scanned automatically, the k8s manifests (16)
get applied by a pipeline, and the cloud (18) is defined in version-controlled files instead of a
console someone forgot the state of.

---

## 2. Concepts in depth

### 2.1 CI vs CD vs CD (the terms, precisely)
- **Continuous Integration**: every push is built + tested + linted on a shared main; small, frequent merges; trunk-based development
- **Continuous Delivery**: every green build is *deployable* (one button); **Continuous Deployment**: every green build *auto-deploys* to prod
- Why fast, reliable CI is the foundation (a slow/flaky pipeline gets bypassed — topic 13's flakiness rule matters here)
- The DORA metrics (deploy frequency, lead time, change-fail rate, MTTR) — how you know your delivery is actually good

### 2.2 The CI pipeline (build it stage by stage)
- Pipeline anatomy: trigger → lint/format/type-check → unit tests → integration tests (testcontainers from topic 13!) → build image (topic 15) → scan (Trivy) → sign (cosign) → push → deploy
- Stages, jobs, dependencies, parallelism, matrix builds (multiple Python versions/arches)
- **Caching** for speed: dependency cache, Docker layer cache (topic 15), test result caching — the difference between a 2-min and a 20-min pipeline
- Fast vs slow suites (topic 13): fail fast on quick checks, gate the slow ones
- Quality gates: coverage floors, security scan thresholds, required reviews, branch protection — and not making them so strict people route around them
- GitHub Actions concretely: workflows, jobs, steps, runners, `services:` (real Postgres/Redis in CI), secrets/OIDC, reusable/composite workflows, environments & approvals
- Artifacts & provenance: what the pipeline produces and how it's traceable (SBOM from topic 15, build attestations)

### 2.3 Deployment strategies ⭐ (how to change prod without breaking it)
- **Rolling** (k8s default, topic 16): gradual replace; simple; the readiness-probe dependency
- **Blue/green**: two full environments, flip traffic; instant rollback; double the resources briefly
- **Canary**: route a small % to the new version, watch metrics (topic 14!), ramp or abort; the safest for risky changes
- **Progressive delivery**: automated canary analysis (Argo Rollouts/Flagger) driving the ramp from SLOs/metrics
- **Feature flags** (LaunchDarkly/Unleash/OpenFeature): decouple *deploy* from *release*; dark launches, kill switches, per-tenant rollout (ties to topic 04 tenancy) — often more important than the deploy strategy itself
- **Database migrations in CD** (the hard part, ties to topic 04): expand/contract (backward-compatible) migrations so app vN and vN+1 both work during a rollout; never a breaking migration in lockstep with code; migration as a pipeline step/Job (topic 16)
- Rollback strategy: image tag revert, k8s rollout undo, and why forward-fix vs rollback is a judgment call — plus the "you can't rollback a destructive migration" rule

### 2.4 GitOps ⭐ (declarative deployment, done right)
- The idea: **git is the single source of truth** for desired state; a controller in the cluster continuously reconciles cluster → git (the topic-16 control loop, applied to deployment)
- **ArgoCD** / Flux: watch a repo, apply manifests, show/heal drift, auto-sync or manual — you *push to git*, not `kubectl apply` to prod
- Push-based CI/CD vs pull-based GitOps — trade-offs (credentials, drift, auditability); why pull-based is more secure (cluster pulls, CI never holds cluster creds)
- Repo structure: app repo vs config/manifest repo; how CI updates the image tag in the config repo → GitOps deploys it
- Environments as branches/folders/overlays (topic 16 Kustomize overlays become your envs); promotion between environments

### 2.5 Infrastructure as Code ⭐
- Why: click-ops isn't reproducible, reviewable, or recoverable; IaC makes infra a versioned, peer-reviewed artifact
- **Declarative vs imperative**; the reconciliation model again (declare desired infra, tool makes it so)
- **Terraform / OpenTofu** deeply enough to be productive:
  - providers, resources, data sources; **state** (what it is, why it's the crux), remote state + locking (S3+DynamoDB), never edit by hand
  - variables, outputs, **modules** (reusable infra components), workspaces/environments
  - `plan` vs `apply` (plan is the safety review), drift detection, `import` for existing resources
  - dependency graph, lifecycle, the destroy/recreate footguns
- **CloudFormation / CDK / Pulumi** — the alternatives (CDK/Pulumi = real code); one line each on when
- Terraform for k8s (provider) vs manifests via GitOps — the sensible division: Terraform for cloud infra (VPC, EKS, RDS — topic 18), GitOps for what runs *in* the cluster
- **Configuration management** (Ansible) vs provisioning (Terraform) — the distinction; immutable infra (rebuild, don't mutate — topic 15) vs config-managed
- Policy as code (OPA/Sentinel/tfsec/checkov): guardrails in the pipeline so IaC can't provision insecure infra (public bucket, open security group — ties topics 07/10/18)
- Secrets in IaC: never in state/plaintext; integrate with secret managers (topic 07/18)

### 2.6 Environments & release management
- Dev → staging → prod parity (12-factor, topic 15); ephemeral **preview environments** per PR (topic 13's e2e envs) and how they're spun up/torn down
- Config & secret management per environment (topic 07); environment promotion flows
- Versioning & release: semantic versioning, changelogs, tagging, release automation (semantic-release)
- Managing the cloud bill in CI (ephemeral envs cost money — auto-teardown)

### 2.7 Pipeline security (the supply chain, end to end)
- **OIDC-based cloud auth** from CI (no long-lived cloud keys in GitHub secrets — the modern must-do); short-lived credentials
- Secret scanning (gitleaks, topic 07), dependency scanning (Dependabot/Renovate + `pip-audit`), SAST (CodeQL/Bandit), image scanning (topic 15) — all as pipeline gates
- **SLSA / supply-chain levels**: provenance, signed artifacts (cosign, topic 15), verifying what you deploy is what you built
- Least-privilege runners/service accounts; protecting the pipeline itself (it can deploy to prod — it's a high-value target); poisoned-PR/dependency risks

### 2.8 Operating delivery
- Deployment observability (topic 14): mark deploys on dashboards, watch golden signals post-deploy, auto-rollback on SLO burn
- Progressive delivery driven by metrics (close the loop with topic 14)
- Runbooks, on-call handoff, and the change-management balance (velocity vs safety — the DORA insight that they're not opposed)

---

## 3. Hands-on labs

> Code in `labs/17_cicd_and_iac/` and `.github/workflows/` in the repo.

**Lab 1 — A real CI pipeline for the todo-app.**
GitHub Actions: lint + type-check → unit tests → integration tests with a real Postgres/Redis via
`services:` (topic 13) → build image (topic 15) → Trivy scan → push to GHCR. Optimize with caching;
measure cold vs warm pipeline time. Add branch protection requiring it green.

**Lab 2 — Sign and attest.**
Add cosign signing + SBOM attestation (topic 15) to the pipeline. Add a step that *verifies* the
signature before deploy — prove an unsigned image is rejected.

**Lab 3 — Deploy strategies on KIND.**
Deploy the todo-app to your KIND cluster (topic 16) three ways: rolling (baseline), blue/green
(two services + traffic flip), and a canary with Argo Rollouts driven by a metric (topic 14).
Trigger a "bad" version and watch the canary auto-abort.

**Lab 4 — Zero-downtime migration in the pipeline.**
Implement an expand/contract migration (topic 04): ship the additive change + backfill, deploy code
that works with both schemas, then the contract migration in a later deploy — all as pipeline
steps/Jobs, with the app serving traffic throughout. Prove no downtime and no errors.

**Lab 5 — GitOps with ArgoCD.**
Install ArgoCD on KIND. Point it at a config repo of your Kustomize overlays (topic 16). Change the
image tag via a commit and watch ArgoCD sync it. Manually `kubectl edit` a live resource and watch
ArgoCD detect+heal the drift. Compare this to Lab 1's push-based deploy in `NOTES.md`.

**Lab 6 — Terraform from zero (against LocalStack).**
Write Terraform for a small stack (S3 bucket + SQS queue + IAM policy) against **LocalStack**
(topic 18 preview). Set up remote state + locking. Run `plan`, read it, `apply`. Change a variable,
plan again, see the diff. `destroy`. Then add `tfsec`/`checkov` and fix a flagged insecure resource.

**Lab 7 — Terraform module + multi-env.**
Refactor Lab 6 into a reusable module; instantiate it for dev and prod with different variables.
Add a policy-as-code check that blocks a public S3 bucket (ties topics 07/10).

**Lab 8 — OIDC cloud auth (no static keys).**
Configure GitHub Actions → cloud via OIDC (against AWS free tier or documented for LocalStack).
Show the pipeline assuming a short-lived role with no long-lived secret stored. Explain the attack this closes.

**Lab 9 — Close the loop.**
Wire deploy markers into Grafana (topic 14); after a deploy, auto-watch the error-rate SLO and
auto-rollback (Argo Rollouts) if it burns. Trigger it deliberately.

## 4. AWS mapping

| Local/tool concept | AWS equivalent | Notes |
|---|---|---|
| GitHub Actions | **CodePipeline + CodeBuild** | Or run Actions against AWS via OIDC (common) |
| GHCR registry | **ECR** (topic 15) | Push target |
| Terraform | Terraform (multi-cloud) / **CDK / CloudFormation** | Terraform is the default multi-cloud choice |
| Remote state | **S3 + DynamoDB lock** | The canonical Terraform backend |
| ArgoCD on KIND | ArgoCD/Flux on **EKS** | GitOps works identically on EKS |
| OIDC from CI | **IAM OIDC provider + assume-role** | No static AWS keys in CI |
| LocalStack (Lab 6) | Real AWS APIs (topic 18) | Same Terraform, real backend |
| Policy as code | tfsec/checkov + **AWS Config / SCPs** | Guardrails at provision + runtime |

---

## 5. Mini-project — "Full automated delivery for the todo-app platform"

In `labs/17_cicd_and_iac/` + repo workflows:

1. CI pipeline: lint/type/test (real deps) → build → scan → sign/SBOM → push, cached and fast, as a required gate
2. IaC (Terraform, LocalStack now / AWS-ready) defining the platform's cloud resources as reusable modules with remote state, policy-as-code, and multi-env
3. GitOps (ArgoCD) deploying the topic-16 overlays; commit-to-deploy; drift detection & self-heal
4. A canary deployment driven by topic-14 metrics with automatic rollback on SLO burn
5. Zero-downtime expand/contract DB migrations as pipeline steps
6. OIDC cloud auth (no static keys), full supply-chain gates (secret/dep/SAST/image scans + signature verification)
7. **`DELIVERY.md`**: the pipeline diagram, deploy-strategy choice + rationale, the migration playbook,
   the GitOps model, and the security posture. (This is the doc that says "I can own production.")

Done = a `git push` safely tests, builds, scans, signs, and progressively deploys with automatic rollback — and the whole infra can be recreated from code.

---

## 6. Self-check — you're done when you can…

1. Distinguish CI, continuous delivery, and continuous deployment, and name the four DORA metrics.
2. Design a CI pipeline stage-by-stage and explain what each gate protects and how you'd keep it fast.
3. Compare rolling vs blue/green vs canary and choose one for a risky change, justifying it with metrics.
4. Explain feature flags and why decoupling deploy from release matters.
5. Walk an expand/contract migration through a rollout and explain why a breaking migration in lockstep is wrong.
6. Explain GitOps and why pull-based reconciliation is more secure than pushing to prod from CI.
7. Explain Terraform state, why it's the crux, and how remote state + locking prevents corruption.
8. Explain the Terraform plan/apply safety model and how policy-as-code stops insecure infra.
9. Explain OIDC-based CI→cloud auth and the risk of long-lived keys it eliminates.
10. Explain SLSA/supply-chain integrity: how you verify what you deploy is what you built.

---

## 7. Resources

- **"Continuous Delivery" (Humble & Farley)** + **"Accelerate" (Forsgren, Humble, Kim)** — the philosophy and the DORA evidence
- **GitHub Actions docs** — workflows, OIDC, caching, environments (your CI platform)
- **Terraform docs + "Terraform Up & Running" (Yevgeniy Brikman)** — the definitive IaC learning path (§2.5)
- **ArgoCD docs + "GitOps" (Weaveworks/Codefresh guides)** — pull-based delivery (§2.4)
- **Argo Rollouts / Flagger docs** — progressive delivery & automated canary (Lab 3/9)
- **SLSA.dev + sigstore/cosign docs** — supply-chain integrity (§2.7)
- **tfsec / checkov / OPA docs** — policy as code
- **OpenFeature / Unleash docs** — feature flags (§2.3)
