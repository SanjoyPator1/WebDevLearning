# 07 — Auth & Security: Identity, Access, and Not Getting Owned

> Phase 3 · Core application concerns · Builds on: 01 (TLS, cookies), 03 (error contracts), 04 (RLS/tenancy)
> Playground: adds **keycloak** (identity provider for OIDC + SAML)

---

## 1. Why this matters

Auth is the one area where a single mistake is catastrophic rather than slow: a leaked token,
a missing authorization check, a JWT verified with `algorithm=none`. You already implemented
JWT auth in the todo-app — this topic is about understanding *why* each piece exists, the
protocols real companies use (OAuth2, OIDC, SAML), and the attack classes you're defending against.

The goal: you can integrate "Login with Google", stand up enterprise SSO, reason about what
lives inside a token, and pass a security review of your own code.

---

## 2. Concepts in depth

### 2.1 Vocabulary first (people conflate these constantly)
- **Authentication** (who are you) vs **Authorization** (what may you do) — different problems, different bugs
- Identity, principal, subject, claim, scope, role, permission — precise definitions
- Identity Provider (IdP) vs Service Provider / Relying Party — the two sides of every SSO flow
- Confidential vs public clients — why a mobile app or SPA can't keep a secret (and what that changes)

### 2.2 Credentials & password handling
- Password hashing done right: bcrypt / argon2 / scrypt — why slow-by-design, salts, work factors
- Never: MD5/SHA-256 raw, homegrown schemes, encrypting (not hashing) passwords
- Credential stuffing, breach corpora, HaveIBeenPwned k-anonymity check; rate-limiting login (ties to 19)
- Account lifecycle security: signup verification, password reset tokens (single-use, expiring, constant-time compare), enumeration avoidance

### 2.3 Sessions vs tokens — the core design axis
- **Server-side sessions**: opaque session id in a cookie, state in Redis/DB. Pros: instant revocation, small cookie. Cons: server state (ties to 01 statelessness, 06 for the store)
- **Stateless JWTs**: signed claims, no server lookup. Pros: scale, no shared store. Cons: revocation is HARD, size, staleness
- The honest verdict: sessions are underrated; use JWTs when you actually need cross-service statelessness
- Cookie security (from 01, now applied): `HttpOnly`, `Secure`, `SameSite=Lax/Strict/None`, domain/path scoping, `__Host-` prefix

### 2.4 JWT — anatomy, precisely (what each item contains)
- Structure: `header.payload.signature`, base64url — **encoded, not encrypted** (anyone can read the payload!)
- **Header**: `alg` (HS256 vs RS256/ES256), `kid` (which key signed this), `typ`
- **Payload / registered claims**: `iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti` — what each is FOR, and validating every one
- **Signature**: HMAC (shared secret, HS*) vs asymmetric (private signs / public verifies, RS*/ES*) — when to use which
- Signing keys & rotation: **JWKS endpoint** (`/.well-known/jwks.json`) — public keys by `kid`, how verifiers fetch & cache them, rotation without downtime
- The classic attacks and defenses: `alg: none`, HS/RS confusion (verifying an RS token with the pubkey as an HMAC secret), missing `aud`/`exp` checks, accepting unsigned
- **JWE** (encrypted JWT) vs **JWS** (signed) — when payload confidentiality is actually needed
- Access token vs refresh token vs ID token — three tokens, three jobs (don't mix them up)

### 2.5 Refresh tokens & token lifecycle
- Short-lived access token + long-lived refresh token — why the split
- Refresh token **rotation** + reuse detection (stolen-token detection): each refresh issues a new one, replay of an old one nukes the family
- Storage: refresh token in `HttpOnly` cookie vs app storage; the SPA dilemma (localStorage = XSS-exposed)
- Logout & revocation strategies for stateless tokens: short TTLs, denylist (`jti` in Redis with TTL=exp), token versioning per user

### 2.6 OAuth2 — delegated authorization (NOT login)
- The mental model: OAuth2 delegates *access to resources*; it is not authentication (that's OIDC's job)
- Roles: resource owner, client, authorization server, resource server
- **Authorization Code flow + PKCE** — the one correct flow for web & mobile today; walk every redirect and parameter
- `state` (CSRF protection) and `code_verifier`/`code_challenge` (PKCE) — what each defends against
- Other grants and when (rarely): client credentials (machine-to-machine — this one you'll use), device code (TVs); **deprecated**: implicit, password grant — know why they died
- Scopes vs your app's permissions; token introspection (opaque tokens) vs local JWT validation — the trade-off

### 2.7 OIDC — authentication on top of OAuth2
- What OIDC adds: the **ID token** (a JWT about the *user*), the `userinfo` endpoint, standard scopes (`openid`, `profile`, `email`)
- **Discovery**: `/.well-known/openid-configuration` — endpoints, supported algs, the JWKS URI — how a client auto-configures
- ID token vs access token: audience and purpose differ — validate the ID token for *login*, present the access token to *APIs*
- "Login with Google/GitHub" is just OIDC — you'll wire it in Keycloak and understand every hop
- Nonce (replay protection for the ID token), `at_hash` — the extra claims OIDC layers on

### 2.8 SAML — the enterprise incumbent
- Why it still matters: nearly every B2B/enterprise SSO ("login with Okta/Azure AD/your-employer") speaks SAML
- XML-based, browser-redirect/POST bindings; **assertions** (signed XML statements about a user)
- Anatomy of what SAML contains: `<AuthnRequest>` (SP→IdP), `<Response>` with signed `<Assertion>`
  (Subject, Conditions incl. `NotOnOrAfter`, AudienceRestriction, AttributeStatement)
- **Certificates in SAML**: IdP signs assertions with its **private key**; SP verifies with the IdP's
  **X.509 public cert** from the IdP metadata; optional SP-signed requests and encrypted assertions —
  contrast this with OIDC's JWKS (cert-in-metadata vs keys-over-JSON-endpoint)
- **Metadata XML** — the exchange artifact: entityID, endpoints (ACS URL), signing certs — both sides import each other's
- SP-initiated vs IdP-initiated SSO; SLO (single logout) and why it's fragile
- The attack surface: XML signature wrapping (XSW), canonicalization bugs, unsigned assertions,
  comment-injection on NameID — **why you use a vetted library and never parse SAML XML by hand**
- SAML vs OIDC decision: OIDC for new/consumer/mobile & APIs; SAML when the enterprise IdP mandates it; many IdPs speak both

### 2.9 Authorization models (the other half of auth)
- RBAC: roles → permissions; role explosion and how to avoid it
- ABAC / PBAC: attribute/policy-based (resource owner, tenant, time, environment) — more expressive
- ReBAC: relationship-based (Google Zanzibar / OpenFGA) — "can user X view doc Y because they're in group Z" — the modern approach for sharing-heavy apps
- Enforcement placement: gateway vs service vs data layer; centralized policy (OPA/Rego, Cedar) vs in-code checks
- Multi-tenant authorization: tie back to 04's RLS — defense in depth (app check + DB RLS)
- The #1 real-world API bug: **BOLA/IDOR** — object-level authz (checking `todo.owner == current_user` on EVERY access, not just at the collection)

### 2.10 The OWASP mindset (defensive baseline)
- OWASP Top 10 walked with a FastAPI lens: broken access control (BOLA), injection (SQL/NoSQL/command),
  SSRF, security misconfig, vulnerable dependencies, auth failures, cryptographic failures
- Input validation as a security boundary (Pydantic is your friend — but validate authorization, not just shape)
- Injection defense: parameterized queries (SQLAlchemy already does this — know why), never string-built SQL
- SSRF: the server-fetches-a-URL feature that lets attackers hit your metadata endpoint (huge in cloud — ties to 18 IAM)
- CORS correctly (from 01/middleware): it is NOT authorization; what it does and doesn't protect
- Security headers: CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`
- Secrets management: env vars → secret managers (Vault, AWS Secrets Manager), rotation, never in git; detecting leaks (gitleaks)
- Dependency & supply-chain hygiene: `pip-audit`, SBOMs, pinning (ties to 15/17)

---

## 3. Hands-on labs

> Code in `labs/07_auth_and_security/`. Add **keycloak** to the playground — it's your IdP for OIDC *and* SAML.

**Lab 1 — Harden the todo-app's own auth.**
Audit the existing JWT setup: is `exp`/`aud`/`iss` validated? `alg` pinned? Add refresh-token
rotation with reuse detection (family invalidation), `HttpOnly`+`SameSite` cookies, and a
`jti` denylist in Redis for logout. Write down each thing you fixed and the attack it closes.

**Lab 2 — Break a JWT on purpose.**
Craft three forged tokens: `alg: none`, RS/HS confusion, and an expired-but-otherwise-valid
token. Prove your verification rejects all three. (If any passes, that's the lesson.)

**Lab 3 — OIDC login with Keycloak.**
Stand up Keycloak, create a realm + client, implement Authorization Code + PKCE login in the
todo-app. Trace every redirect with browser devtools. Validate the ID token against Keycloak's
JWKS (fetch + cache by `kid`). Add "Login with Google" as an upstream IdP in Keycloak.

**Lab 4 — SAML SSO with Keycloak.**
Configure Keycloak as a SAML IdP; make the todo-app a SAML SP (use `python3-saml` / a vetted
lib — do NOT hand-roll). Exchange metadata, complete SP-initiated SSO, inspect the signed
assertion XML, and verify the signature against the IdP cert from metadata. Compare the whole
experience to Lab 3's OIDC flow in `NOTES.md`.

**Lab 5 — Machine-to-machine.**
Client-credentials grant: a second service gets a token from Keycloak and calls the todo-app
API with it (no user involved). Scope it down; verify scope enforcement.

**Lab 6 — Authorization / BOLA hunt.**
Deliberately introduce an IDOR (`GET /todos/{id}` without ownership check) and write an
exploit script that reads another user's todos. Fix with object-level checks in the service
layer, then add DB-level RLS (from 04) as defense in depth. Re-run the exploit — blocked twice.

**Lab 7 — OWASP pass + security headers.**
Add CSP/HSTS/security headers middleware, run `pip-audit` + a `bandit` scan, wire `gitleaks`
as a pre-commit hook, and move all secrets to a `.env` + document a Vault/Secrets-Manager plan.

---

## 4. AWS mapping

| Local concept | AWS equivalent | Notes |
|---|---|---|
| Keycloak (OIDC IdP) | **Cognito User Pools** | Managed OIDC IdP; hosted UI; social + SAML federation |
| Keycloak (SAML IdP/broker) | Cognito / **IAM Identity Center** | Enterprise SSO federation, SAML & OIDC |
| Your JWT validation at the edge | **API Gateway JWT/Cognito authorizers** | Offload token validation to the gateway |
| `jti` denylist / sessions | Cognito token revocation | Managed revocation & refresh |
| Secrets in .env | **Secrets Manager / SSM Parameter Store** | Rotation, encryption, IAM-scoped access |
| Authorization policies | **Verified Permissions (Cedar)** / OPA on EKS | Externalized authz |
| App-role → resource access | **IAM roles** (the cloud's own authz) | SSRF→metadata risk lives here (topic 18) |

---

## 5. Mini-project — "Enterprise-ready auth for todo-app"

In `labs/07_auth_and_security/`:

1. Local username/password (argon2) **plus** OIDC social login **plus** SAML enterprise SSO — all via Keycloak
2. Access + refresh tokens with rotation, reuse detection, and denylist logout
3. RBAC roles (owner/member/viewer per tenant) enforced in the service layer + RLS in the DB (defense in depth)
4. Every object access does an ownership/authorization check — prove with the Lab 6 exploit that it's closed
5. Security headers, `pip-audit`/`bandit` clean, secrets externalized, gitleaks pre-commit
6. **`THREAT_MODEL.md`**: for each protocol used, what's inside each token/assertion, which key
   signs & which verifies, and the attack each safeguard defends against. (Portfolio-grade doc.)

---

## 6. Self-check — you're done when you can…

1. Explain authN vs authZ and give a real bug that is purely one and not the other.
2. Argue sessions vs JWTs for a given system, and describe how you'd revoke a stateless JWT three ways.
3. Name every JWT claim you validate and the attack skipping each one enables; explain `alg:none` and RS/HS confusion.
4. Explain what a JWKS endpoint is, what `kid` does, and how key rotation works without breaking live tokens.
5. Walk the Authorization Code + PKCE flow end to end and say what `state` and `code_verifier` each protect.
6. Explain the difference between OAuth2 and OIDC, and between an access token and an ID token.
7. Describe what a SAML assertion contains, which key signs it and which verifies it, and where the certs come from — contrasted with OIDC's JWKS.
8. Explain BOLA/IDOR and why collection-level auth isn't enough; show the fix at two layers.
9. Compare RBAC vs ABAC vs ReBAC and pick one for a document-sharing feature.
10. List your top OWASP concerns for a FastAPI app and the concrete mitigation for each.

---

## 7. Resources

- **OWASP Cheat Sheet Series** (Authentication, Session Management, JWT, Password Storage, SAML Security) — the practical bible; bookmark it
- **OAuth 2.0 Simplified — Aaron Parecki** ([oauth.net](https://oauth.net)) — the clearest OAuth/OIDC explainer anywhere
- **jwt.io** — decode & inspect tokens; the debugger you'll use in Lab 2
- **OpenID Connect spec (core) + your IdP's docs** — discovery, ID token, flows
- **Okta Developer Blog** — excellent, vendor-neutral-enough deep dives on OIDC, SAML, PKCE
- **"SAML is insecure by design"–style writeups + the XSW papers** — read before trusting any hand-rolled SAML
- **Google Zanzibar paper / OpenFGA docs** — for ReBAC in 2.9
- **PortSwigger Web Security Academy** — free, hands-on labs for the OWASP attack classes (JWT, SSRF, access control)
