# 18 — AWS for Backend: The Cloud Under Everything You've Built

> Phase 6 · Infrastructure & delivery · Builds on: every "AWS mapping" section so far
> Local: **LocalStack** (emulate most AWS services) + everything you've already stood up locally

---

## 1. Why this matters

Every topic so far ended with an "AWS mapping" table — this topic ties them together into how a
real backend actually lives in the cloud. You've learned the *open-source thing* first (Postgres,
Redis, MinIO, Redpanda, Keycloak, Prometheus, KIND) exactly so that the AWS managed equivalents are
"the thing I know, operated for me" rather than magic.

The goal here isn't AWS certification trivia. It's: understand the primitives that everything runs
on (IAM, VPC, the compute options), know how to run *your* stack (the todo-app platform) on AWS,
and — critically — be able to do most of it locally with **LocalStack** so you learn without a
scary bill. This is also where cloud *security* (IAM, the SSRF-to-metadata attack from topic 07)
and *cost awareness* become real.

---

## 2. Concepts in depth

### 2.1 How to think about the cloud (framing before services)
- The shared responsibility model: what AWS secures vs what you secure (misconfiguration is YOUR job — topic 07/10)
- Regions, Availability Zones, edge locations — designing for AZ failure (Multi-AZ everywhere that matters)
- The mental model: managed services trade control + cost for undifferentiated-heavy-lifting removed; when that trade is right vs wrong
- Well-Architected Framework pillars (operational excellence, security, reliability, performance, cost, sustainability) — a checklist you can actually use

### 2.2 IAM — the foundation of everything ⭐
- The model: **principals** (users, roles) → **policies** (JSON: effect, action, resource, condition) → what's allowed
- **Roles vs users**: why humans + workloads should assume **roles** (short-lived creds via STS) and you should have almost no long-lived access keys
- **Least privilege** in practice; policy evaluation (explicit deny > allow > implicit deny); the confused-deputy problem
- Instance profiles / **IRSA / EKS Pod Identity** (topic 16): how a pod/instance gets creds *without* stored secrets — the secure pattern
- **The metadata endpoint (169.254.169.254)** and the SSRF-to-credential-theft attack (topic 07) — IMDSv2 as the fix; why this is one of the most exploited cloud misconfigs
- Cross-account access, SCPs (org guardrails), permission boundaries — awareness
- This connects to everything: S3 tenant isolation (topic 10), CI OIDC (topic 17), secrets access (topic 07)

### 2.3 Networking — VPC ⭐ (topic 01, now in the cloud)
- **VPC, subnets, CIDR** (topic 01's CIDR pays off), route tables — your private network in the cloud
- Public vs private subnets; **Internet Gateway** vs **NAT Gateway** (topic 01's NAT — and the NAT bill surprise)
- **Security Groups** (stateful, instance-level) vs **NACLs** (stateless, subnet-level) — the cloud firewall, and the difference that confuses everyone
- VPC endpoints (reach S3/other services without the public internet — security + cost), PrivateLink
- Load balancers revisited (topic 01): ALB (L7) vs NLB (L4) as managed services; where TLS terminates (ACM)
- DNS (topic 01): Route 53 — hosted zones, record types, routing policies, health checks
- Designing a sane VPC for the todo-app: where the API, DB, cache, and NAT live and why

### 2.4 Compute — the options and how to choose ⭐
The decision that shapes everything else. Walk the spectrum:
- **EC2** — raw VMs; full control, most ops; when you actually need it; instance families, spot vs on-demand vs reserved/savings plans
- **ECS (+ Fargate)** — containers (topic 15) without k8s; Fargate = serverless containers (no nodes to manage); the pragmatic default for many teams
- **EKS** — managed Kubernetes (topic 16); when the k8s power is worth the complexity (and topic 16's "when NOT to")
- **Lambda** — serverless functions; event-driven, scale-to-zero, per-ms billing; cold starts; the 15-min limit (why topic 08's GPU/long jobs DON'T go here); Lambda + API Gateway (topic 03) pattern
- **App Runner / Elastic Beanstalk** — PaaS-like, "just run my container/app"
- A decision framework: control vs ops-burden vs cost vs scale-pattern → which compute; and mixing them (Lambda for glue, ECS/EKS for the API, EC2/EKS-GPU for inference)

### 2.5 Data services (topics 04/05/06, managed)
- **RDS** (Postgres — topic 04): Multi-AZ, read replicas, automated backups/PITR, parameter groups; **Aurora** (the cloud-native rewrite); **RDS Proxy** (topic 04's PgBouncer, managed — the Lambda+Postgres answer)
- **ElastiCache** (Redis/Valkey — topic 06); **DynamoDB** (topic 05 — the one truly serverless DB, single-table design pays off); **OpenSearch Service** (topic 05)
- **S3** (topic 10) — the storage backbone; storage classes, lifecycle, the security model you already learned; **EFS/EBS** for the block/file cases
- Choosing managed vs self-hosted-on-EC2/EKS: the ops/cost/control trade (mostly: use managed for stateful)

### 2.6 Messaging & events (topics 08/11, managed)
- **SQS** (topic 08 queues — visibility timeout, DLQ, FIFO), **SNS** (fan-out), **EventBridge** (routing/rules/schedules — topic 08 cron & topic 11 event bus)
- **MSK / Kinesis** (topic 11 log/streaming); **Step Functions** (topic 12 saga orchestration)
- The "AWS-native event-driven" reference architecture and how it maps to what you built locally

### 2.7 Security, secrets & compliance (topic 07, cloud edition)
- **Secrets Manager / SSM Parameter Store** (topic 07/17 secrets) — rotation, IAM-scoped access
- **KMS** (topic 10's per-tenant encryption) — envelope encryption, key policies, the "revoke key = revoke data" model
- **Cognito** (topic 07 auth — managed OIDC/SAML IdP); **WAF** (L7 protection — topic 19 rate limiting/DDoS), **Shield** (DDoS)
- **GuardDuty / Security Hub / Config / CloudTrail** — detection, posture, audit log (CloudTrail = who did what, the forensics backbone)
- Certificate management: **ACM** (topic 01 TLS, free certs, auto-renew)

### 2.8 Observability & operations (topic 14, cloud edition)
- **CloudWatch** (metrics, logs, alarms, dashboards), **X-Ray** (tracing), **Managed Prometheus/Grafana**, **ADOT** (managed OpenTelemetry) — topic 14's stack, managed
- The mapping: your Prometheus→AMP, Grafana→AMG, Loki→CloudWatch Logs, Jaeger→X-Ray (all OTel-portable)

### 2.9 Cost awareness ⭐ (the skill that gets you promoted)
- The pricing mental model: compute (right-sizing, spot, savings plans), storage (tiers), and the one that surprises everyone — **data transfer / egress** (cross-AZ, cross-region, internet-out; why VPC endpoints & CDNs save money — topics 06/10)
- NAT Gateway, idle load balancers, un-deleted volumes/snapshots, over-provisioned RDS — the classic money leaks
- Cost tooling: Cost Explorer, Budgets + alerts, tagging for allocation, the Well-Architected cost pillar
- Serverless vs always-on cost curves (Lambda cheap at low/spiky traffic, expensive at sustained high; the crossover point)
- FinOps mindset: cost as a first-class engineering metric, per-tenant cost (topic 04 tenancy → per-tenant billing)

### 2.10 LocalStack & learning without a bill ⭐
- What LocalStack emulates (S3, SQS, SNS, DynamoDB, Lambda, IAM-ish, and more) and its limits (not a perfect prod substitute; some services partial/pro-only)
- Running your Terraform (topic 17) against LocalStack → same code, real AWS later (just swap the endpoint/provider)
- The free-tier + budget-alarm safety setup for the few things you should touch on real AWS
- What genuinely needs real AWS to learn (IAM nuances, VPC networking behavior, real egress costs) vs what LocalStack teaches fine

---

## 3. Hands-on labs

> Code in `labs/18_aws_for_backend/`. Add **localstack** to the playground; use it for most labs. Real AWS only where noted (free tier + budget alarm first!).

**Lab 1 — IAM by breaking it.**
Against LocalStack (and optionally real free-tier): create a role with a least-privilege policy for
the todo-app to access ONE S3 prefix (topic 10 tenant isolation). Try an action outside the policy →
denied. Add a resource condition. Write the policy-evaluation logic (deny/allow/implicit) in your notes.

**Lab 2 — The metadata SSRF attack (security eye-opener).**
On a real (or simulated) EC2/pod, demonstrate how an SSRF vulnerability (topic 07) reaching
`169.254.169.254` steals role credentials with IMDSv1, and how **IMDSv2** blocks it. Document the fix.

**Lab 3 — Design and provision a VPC (Terraform).**
With Terraform (topic 17) against LocalStack: a VPC with public + private subnets, IGW, NAT,
security groups. Place the todo-app (public-facing via ALB) and its DB (private only). Explain every
routing/security-group decision. (This is topic 01's networking made cloud-concrete.)

**Lab 4 — Run the todo-app three ways.**
Deploy the todo-app image (topic 15) to: (a) ECS Fargate, (b) EKS (topic 16 — your KIND manifests
now target a real/simulated cluster), and (c) a Lambda + API Gateway variant (topic 03). Compare
effort, cold-start, scaling, and cost in a table. Decide which you'd actually use and why.

**Lab 5 — Managed data services swap.**
Point the todo-app at RDS Postgres (topic 04) + ElastiCache (topic 06) + S3 (topic 10) instead of
the local containers — via config only (12-factor, topic 15). Add RDS Proxy and connect the
connection-math lesson (topic 04). (LocalStack for S3/DynamoDB; RDS needs real/free-tier or a documented plan.)

**Lab 6 — AWS-native event-driven (LocalStack).**
Rebuild topic 08/11's flows with SQS + SNS + EventBridge on LocalStack: enqueue a job to SQS with a
DLQ, fan out an event via SNS, schedule a cron via EventBridge. Compare to your RabbitMQ/Redpanda
implementations.

**Lab 7 — Secrets, KMS, and per-tenant keys.**
Store the todo-app's secrets in Secrets Manager (topic 07/17); encrypt S3 objects with KMS and model
per-tenant keys (topic 10). Demonstrate that revoking a key revokes access to that tenant's data.

**Lab 8 — Cost teardown.**
Take your Lab 3/4 architecture and produce a cost estimate (Pricing Calculator): identify the
NAT Gateway, egress, and idle-LB costs. Redesign to cut them (VPC endpoint, CDN from topic 06,
scale-to-zero). Set up a Budget alarm on real AWS. Write the before/after cost story.

**Lab 9 — Full IaC platform (capstone bridge).**
Everything in Terraform modules (topic 17): VPC + EKS/ECS + RDS + ElastiCache + S3 + SQS + IAM,
multi-env, policy-as-code (tfsec) clean. Deploy the todo-app platform end to end on LocalStack
(real-AWS-ready). This is the infra layer of topic 21's capstone.

## 4. Local ↔ AWS reference (the whole course, consolidated)

| What you learned locally | AWS service | Topic |
|---|---|---|
| Postgres + PgBouncer | RDS/Aurora + RDS Proxy | 04 |
| MongoDB / DynamoDB-local / OpenSearch | DocumentDB / DynamoDB / OpenSearch Service | 05 |
| Redis (cache) | ElastiCache | 06 |
| Keycloak | Cognito / IAM Identity Center | 07 |
| RabbitMQ / ElasticMQ | SQS / Amazon MQ | 08 |
| Redis pub/sub backplane | ElastiCache / API GW WebSockets | 09 |
| MinIO | S3 (+ CloudFront) | 10 |
| Redpanda | MSK / Kinesis | 11 |
| Second service + resilience | Cloud Map / App Mesh / Step Functions | 12 |
| testcontainers | Same in CodeBuild/Actions | 13 |
| Prometheus/Grafana/Loki/Jaeger | AMP / AMG / CloudWatch / X-Ray | 14 |
| Local registry + images | ECR | 15 |
| KIND | EKS (+ Karpenter, ALB controller, IRSA) | 16 |
| GitHub Actions + Terraform + ArgoCD | CodePipeline/OIDC + Terraform + ArgoCD on EKS | 17 |

---

## 5. Mini-project — "The todo-app platform, cloud-native (LocalStack, AWS-ready)"

In `labs/18_aws_for_backend/`, tie the whole course together at the infra level:

1. Full VPC (public/private subnets, SGs, NAT/endpoints) designed and provisioned via Terraform (topic 17)
2. Compute decision made and documented: run the platform on ECS Fargate or EKS (topic 16), with the Lambda variant explored
3. Managed data layer: RDS+Proxy (topic 04), ElastiCache (topic 06), S3+KMS (topic 10), DynamoDB where it fits (topic 05)
4. AWS-native events: SQS+DLQ, SNS, EventBridge (topics 08/11)
5. IAM least-privilege throughout (IRSA/roles, no static keys), secrets in Secrets Manager, IMDSv2, CloudTrail on
6. Observability via CloudWatch/X-Ray or OTel→managed (topic 14); a cost estimate + Budget alarm + the egress/NAT optimizations
7. **`CLOUD.md`**: the architecture diagram, the compute/data decisions + rationale, the security posture (IAM, VPC, encryption, the SSRF/IMDSv2 note), and the cost analysis. (This is a staff-level design doc.)

Done = the entire platform is defined in code, runs on LocalStack (and would run on real AWS with a provider swap), is least-privilege secured, and you can defend every cost line.

---

## 6. Self-check — you're done when you can…

1. Explain the shared responsibility model and give a misconfiguration that's squarely your fault.
2. Explain IAM roles vs users, why workloads assume roles, and how a pod gets creds without stored secrets (IRSA).
3. Explain the metadata-endpoint credential-theft attack and how IMDSv2 stops it (tie to topic 07 SSRF).
4. Design a VPC for a web app + private DB and justify subnets, IGW/NAT, and security groups vs NACLs.
5. Choose EC2 vs ECS/Fargate vs EKS vs Lambda for four workloads (API, cron glue, GPU inference, spiky webhook) with reasons.
6. Explain why RDS Proxy exists in terms of topic 04's connection math and Lambda's model.
7. Map five things you built locally to their managed AWS services and state what you gain and lose.
8. Explain the top cloud cost surprises (egress, NAT, idle LBs) and concrete ways to cut each.
9. Explain what LocalStack does and doesn't let you learn, and what genuinely needs real AWS.
10. Explain envelope encryption / KMS and the per-tenant-key isolation model (tie to topic 10).

---

## 7. Resources

- **AWS Well-Architected Framework + the Security & Cost pillars** — the framing and checklists (§2.1, 2.9)
- **"AWS Certified Solutions Architect" study materials (Adrian Cantrill / Stephane Maarek)** — even if you don't sit the exam, the best structured tour of the services
- **AWS docs per service** — IAM, VPC, ECS/EKS, RDS, S3 user guides (reference, not cover-to-cover)
- **LocalStack docs** — what's emulated and how to point Terraform/boto3 at it (§2.10)
- **"AWS security" — the IAM/VPC/IMDSv2 writeups + flaws.cloud / flaws2.cloud** — learn cloud security by exploiting it
- **Corey Quinn (Last Week in AWS) + AWS Pricing Calculator** — cost realism and FinOps culture
- **"The Good Parts of AWS" (Daniel Vassallo)** — an opinionated, refreshingly short "just use these" guide
