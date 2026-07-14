# 10 — File Storage & Media: Uploads, Object Storage, CDNs, and Multi-Tenant Security

> Phase 3 · Core application concerns · Builds on: 01 (HTTP, CDN), 06 (caching/CDN), 07 (authz/tenancy), 08 (media jobs)
> Playground: adds **minio** (S3-compatible)

---

## 1. Why this matters

Almost every app stores files: avatars, attachments, exports, uploaded video, ML artifacts. Do
it naively (files on the app server's disk, streamed through your API) and you get: servers that
can't scale horizontally (files stranded on one box), an API process pinned moving bytes,
and — the scary one — **tenants able to read each other's files**.

Your todo-app already has an `uploads/` folder with a file in it (local disk) — this topic
replaces that with real object storage, moves the bytes off your API via presigned URLs, puts a
CDN in front for delivery, and — the part you specifically asked about — makes multi-tenant and
per-user file access genuinely secure.

---

## 2. Concepts in depth

### 2.1 Storage models — and why object storage wins for user files
- Block (disks/EBS) vs file (NFS/EFS) vs **object** (S3/MinIO) — data model and access pattern of each
- Why local disk fails: doesn't survive horizontal scaling (topic 01), container restarts (topic 15), or node loss (topic 16)
- Object storage model: buckets, objects, keys (the "path" is just a string), metadata, unlimited scale, HTTP API
- Durability vs availability numbers (the "11 nines" story) and what they actually mean
- Storage classes / tiers (hot vs cold/archive) and lifecycle transitions

### 2.2 The upload/download architecture (the core pattern)
- **The anti-pattern**: client → your API → storage. Your API process moves every byte (topic 02
  threadpool/loop cost), caps at your bandwidth, and can't scale. Avoid.
- **Presigned URLs (the right way)**: your API signs a time-limited URL; client uploads/downloads
  **directly to/from storage**, bytes never touch your API. You keep control (you decide who gets a URL) without being in the data path.
- Presigned **PUT/POST** for upload, presigned **GET** for download; expiry, allowed size/content-type constraints on the policy
- **Multipart upload**: large files split into parts, parallel upload, resumable, assembled server-side; when it kicks in and why
- Direct browser upload with a POST policy (constrain content-length-range, content-type, key prefix)

### 2.3 Key/namespace design (this is where security starts)
- Keys are just strings — but the layout is your security and organization model
- **Tenant/user prefixing**: `tenant_{tid}/user_{uid}/todos/{todo_id}/{uuid}_{filename}` — prefix
  encodes ownership so it's checkable and IAM-scopable
- Never trust the client-supplied filename as the key (path traversal `../`, collisions, injection);
  generate a UUID key, store original name in metadata/DB
- Content-addressed storage (hash as key) for dedup; when it helps
- Metadata belongs in your DB (owner, tenant, size, content-type, virus-scan status), not only on the object

### 2.4 Multi-tenant & per-user file security ⭐ (the part you asked about)
The scenario: many tenants' (and users') files in **one bucket**, separated by folders/prefixes —
how do you guarantee no one reads someone else's files? Defense in depth, several layers:

- **Layer 0 — buckets are private by default.** Block all public access; nothing is world-readable.
  There are NO public object URLs — every access is mediated (presigned URL or through your API).
- **Layer 1 — application authorization (primary gate).** Before signing ANY URL, your API checks
  the DB: does this user/tenant own this object? (object-level authz / anti-BOLA from topic 07).
  The prefix in the key is compared against the caller's tenant/user. **This is the main defense** —
  a presigned URL is only ever minted for an object the caller is authorized to touch.
- **Layer 2 — presigned URLs are per-object and short-lived.** A signed GET grants access to *one*
  key for *minutes*. It can't be edited to point at another tenant's key (the signature covers the key).
  Leaked URL = one file, briefly — not the bucket.
- **Layer 3 — scoped credentials (STS / assume-role with session policies).** When a client or
  service needs broader access, issue **temporary credentials scoped to a prefix**: a session policy
  that only allows `s3:GetObject` on `tenant_{tid}/*`. Even a compromised credential can't escape the
  tenant's prefix. (MinIO supports STS `AssumeRole` + policies; AWS uses IAM + STS.)
- **Layer 4 — bucket policies / IAM prefix conditions.** Policies with `s3:prefix` conditions and
  `${aws:username}`-style variables enforce prefix isolation at the storage layer, independent of app bugs.
- **Layer 5 — encryption & per-tenant keys.** Server-side encryption (SSE) always on; for strong
  isolation, **per-tenant KMS keys** (SSE-KMS) so a tenant's objects are cryptographically separable
  and key access is itself IAM-controlled (revoke the key → revoke the data). Client-side encryption for the paranoid.
- **When to use separate buckets per tenant** instead of prefixes: compliance/data-residency,
  very large tenants, per-tenant lifecycle/billing — vs the prefix model's simplicity and scale limits (bucket count caps). Decision table.
- **Cross-tenant leakage checklist**: public-access block on, no wildcard bucket policy, authz
  before every sign, key contains tenant, STS scoped, logging on — and a test that *tries* to cross tenants and fails (Lab 5).

### 2.5 CDN & media delivery (ties to topics 01 & 06)
- Why serve files through a CDN: edge caching, latency, offload origin bandwidth, range requests for video
- Origin = your bucket (or your API); CDN caches objects at the edge (recall cache keys & `s-maxage` from topic 06)
- Cache invalidation for files: versioned keys / query strings vs purge APIs (immutable content + versioned URL = best)
- Range requests & streaming media (video scrubbing) — how the CDN + object store handle `Range` headers

### 2.6 Securing private files behind a CDN ⭐ (your other question)
Public assets are easy; **private, per-user/tenant files through a CDN** need signed access —
and the mechanism differs per CDN:

- The problem: a CDN caches at the edge, but private files must not be served to just anyone who
  has the URL — you need auth *at the edge*, not just at the origin.
- **Signed URLs** (per-object): CDN validates a signature/expiry on each URL — like presigned S3
  URLs but enforced by the CDN. Good for one-off downloads; unique URL per object.
- **Signed cookies**: one signed cookie grants access to a *set* of paths (e.g., `tenant_{tid}/*`)
  for a session — better when a page loads many private assets (galleries, video segments) so you
  don't sign every URL. The cookie is scoped by path and expiry.
- **CloudFront specifics**: signed URLs vs signed cookies (key pairs / key groups), Origin Access
  Control (OAC) so the bucket only trusts CloudFront (never public), path-pattern behaviors,
  Lambda@Edge/CloudFront Functions for custom auth (validate a JWT at the edge — ties to topic 07)
- **Other CDNs**: Cloudflare (signed URLs / Access / Workers doing auth at edge), Fastly (VCL/signed
  URLs), Akamai token auth — same *concepts* (signed token, expiry, path scope), different config surface
- **Tenant isolation through the CDN**: signed cookie/URL scoped to the tenant's path prefix +
  OAC-locked private origin = the CDN never serves a tenant file without a valid, tenant-scoped token
- Cache-key caution: don't let a private object get cached under a key another tenant could hit
  (vary/segment the cache correctly, or don't cache authenticated private objects at all)

### 2.7 Media processing pipelines (ties to topic 08)
- The pattern: upload → event/job → process (thumbnail, transcode, virus scan, EXIF strip, OCR) → store derivatives → notify (topic 09)
- Event triggers: bucket notifications (S3 events / MinIO webhooks) → queue → worker fleet (topic 08)
- Image processing (Pillow/ImageMagick/libvips), video transcoding (ffmpeg) — CPU/GPU heavy, so it's the topic-08 §2.7 pattern
- **Virus/malware scanning** (ClamAV) on untrusted uploads before they're marked usable; quarantine flow
- Derivative management: naming, on-the-fly vs precomputed, cleanup of orphaned derivatives

### 2.8 Operational concerns
- Lifecycle policies: expire temp uploads, transition old files to cold storage, delete on account closure (GDPR)
- Cost model: storage + requests + **egress** (the bill that surprises everyone — CDN reduces it)
- Consistency: read-after-write behavior; orphan handling (DB row without object, object without row) and reconciliation
- Backup/versioning: object versioning, MFA-delete, replication (cross-region) for DR
- Quotas & abuse: per-tenant storage limits, upload rate limits (topic 19), max file size enforcement (before signing)

---

## 3. Hands-on labs

> Code in `labs/10_file_storage_and_media/`. Add **minio** to the playground (S3-compatible; boto3 works against it).

**Lab 1 — Replace local disk with object storage.**
Migrate the todo-app's existing `uploads/` (local disk) to MinIO. Attachments on todos now live
in a bucket. Confirm the app is now stateless (run 2 replicas from topic 01 — both serve the same files).

**Lab 2 — Presigned upload & download (get out of the data path).**
Implement presigned PUT for upload and presigned GET for download. Client uploads directly to
MinIO; your API only signs. Verify with the browser network tab that bytes never hit your API.
Constrain the upload policy (max size, content-type, key prefix).

**Lab 3 — Multipart, resumable upload.**
Presigned multipart upload for a large (>100MB) file with parallel parts and resume-after-failure.
Measure vs single-PUT.

**Lab 4 — Tenant/user key design + app authorization.**
Adopt `tenant_{tid}/user_{uid}/...` keys. Enforce object-level authz: the API refuses to sign a
URL unless the caller owns the key's prefix. Store file metadata in Postgres (owner, tenant, size, type).

**Lab 5 — Try to break tenant isolation (the security lab).**
Write an attacker script: as tenant A, attempt to (a) request a presigned URL for tenant B's key,
(b) edit a valid presigned URL to point at B's key, (c) list B's prefix. All must fail. Then add
**STS scoped credentials** (MinIO AssumeRole with a prefix-scoped session policy) and prove even
raw S3 calls with those creds can't escape `tenant_A/*`. Document each layer that stopped the attack.

**Lab 6 — Per-tenant encryption (bonus).**
Enable SSE; explore per-tenant keys (MinIO KMS/KES or documented AWS SSE-KMS design). Explain how
revoking a key revokes access to a tenant's data.

**Lab 7 — CDN in front, public assets.**
Put a CDN/edge cache (nginx `proxy_cache` as a local stand-in, or Cloudflare if you have a domain)
in front of MinIO for public assets. Verify edge cache HITs, versioned-URL invalidation, and range
requests on a video.

**Lab 8 — Private files through the CDN (signed access).**
Serve *private* per-tenant files via signed access: implement signed-URL and signed-cookie style
access (locally simulate the token check at the proxy; document the CloudFront signed-cookie +
OAC design for AWS). Prove a tenant-scoped signed cookie can fetch `tenant_A/*` but not `tenant_B/*`.

**Lab 9 — Media pipeline (ties to 08 & 09).**
On upload, fire a MinIO bucket notification → queue → worker that generates thumbnails + runs a
ClamAV scan; mark the file usable only after scan passes; push a "ready" event to the UI via topic 09.

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| MinIO bucket | **S3** | Same API; boto3 code is identical (swap endpoint) |
| Presigned URLs | S3 presigned URLs | Identical concept & API |
| STS AssumeRole + session policy | **STS + IAM** (prefix-scoped policies) | The real per-tenant credential scoping |
| Block-public-access + policies | S3 Block Public Access + bucket policies | Layer 0 & 4 of the security model |
| SSE / per-tenant keys | **SSE-S3 / SSE-KMS** + KMS keys | Layer 5; KMS key = revocable data access |
| Bucket notifications | S3 Event Notifications → SQS/SNS/Lambda | Media pipeline trigger (topic 08) |
| CDN edge cache | **CloudFront** | Signed URLs/cookies, OAC, behaviors, edge functions |
| Signed private delivery | CloudFront signed cookies + OAC | The §2.6 pattern, productized |
| Lifecycle/versioning | S3 Lifecycle, Versioning, Replication | Cost tiering + DR |
| EFS/EBS (contrast) | when you actually need file/block, not object | Rarely for user uploads |

---

## 5. Mini-project — "Secure multi-tenant file service for todo-app"

In `labs/10_file_storage_and_media/`:

1. All attachments in MinIO, app fully stateless, `tenant/user/...` key design
2. Presigned upload (multipart for large) + presigned download; API never in the byte path
3. Object-level authorization before every sign + Postgres metadata; **STS prefix-scoped creds** for isolation
4. CDN in front: public assets cached at edge; **private per-tenant files via signed cookies/URLs** with OAC-locked private origin
5. Upload → job → thumbnail + ClamAV scan → "ready" event to UI (topics 08 + 09)
6. Lifecycle: temp uploads expire, per-tenant storage quota enforced before signing
7. **`STORAGE_SECURITY.md`**: the full defense-in-depth model, the tenant-isolation test results
   from Lab 5, and the CDN signed-access design — written so a security reviewer is satisfied.

Done = your Lab 5 attacker script fails at every layer, and private files are only reachable through short-lived, tenant-scoped, signed access.

---

## 6. Self-check — you're done when you can…

1. Explain why user files don't belong on the app server's local disk, in terms of topics 01/15/16.
2. Explain the presigned-URL pattern and why it keeps your API out of the data path while preserving access control.
3. Explain when multipart upload matters and what it buys (resume, parallelism).
4. Design a tenant/user key layout and explain how the prefix becomes the unit of security.
5. Walk all layers that stop tenant A from reading tenant B's file, and identify which one is the PRIMARY gate.
6. Explain STS/assume-role prefix-scoped credentials and why they contain a credential leak to one tenant.
7. Explain how per-tenant KMS keys make data isolation cryptographic and revocable.
8. Contrast prefix-per-tenant vs bucket-per-tenant and pick one for a given compliance requirement.
9. Explain signed URLs vs signed cookies for private CDN delivery and when you'd use each, plus what OAC does.
10. Sketch a media pipeline from upload event to "ready" notification, naming the topic-08 and topic-09 pieces.

---

## 7. Resources

- **AWS S3 docs — presigned URLs, Block Public Access, bucket policies, STS, SSE-KMS** — the security model source of truth
- **MinIO docs — presigned URLs, STS AssumeRole, bucket notifications, KES/encryption** — your local hands-on reference
- **AWS CloudFront docs — signed URLs vs signed cookies, Origin Access Control (OAC), edge functions** — for §2.6 and Lab 8
- **"S3 bucket security" writeups (flaws.cloud, common S3 misconfig case studies)** — learn isolation by seeing it fail
- **AWS Well-Architected — Security Pillar (data protection)** — the defense-in-depth framing
- **ffmpeg & libvips docs** — for the media-processing lab
- **boto3 S3 docs** — the client you'll use against both MinIO and S3 unchanged
