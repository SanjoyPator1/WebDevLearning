# 04 — TLS

## Why this matters

TLS is the "S" in HTTPS. It's the difference between anyone on the network reading your users'
passwords and nobody being able to. As a backend engineer you'll configure it (certs on a load
balancer/reverse proxy), debug it (expired certs, chain errors, handshake failures showing up in
your p99), and reason about *where* it terminates. This file is the working mental model.

---

## The three guarantees

TLS gives you three distinct things. Keep them separate in your head — different mechanisms provide each:

1. **Confidentiality** — nobody can *read* the traffic (encryption).
2. **Integrity** — nobody can *tamper* with the traffic undetected (message authentication codes).
3. **Authenticity** — you're really talking to `example.com`, not an impostor (certificates).

A common mistake is to think TLS is "just encryption." The **authenticity** part — proving the server
is who it claims — is what stops a man-in-the-middle from silently sitting between you and the server,
and it's entirely about certificates.

---

## The building blocks (just enough crypto)

- **Symmetric encryption** (e.g. AES): one shared key encrypts and decrypts. Fast. Problem: how do
  both sides get the shared key without an eavesdropper seeing it?
- **Asymmetric encryption** (public/private key pairs): what one key encrypts, only the *other* can
  decrypt. Slow, but solves key exchange. Also enables **signatures**: sign with the private key,
  anyone can verify with the public key.

**How TLS uses both:** asymmetric crypto during the handshake to securely agree on a shared symmetric
key, then fast symmetric crypto for the actual data. Best of both worlds.

---

## The handshake (conceptual)

The handshake happens *after* the TCP handshake (file 02) and *before* any HTTP:

```
TCP handshake done ──►  TLS handshake  ──►  encrypted HTTP flows
```

Roughly, in the handshake the client and server:
1. Agree on the TLS **version** and **cipher suite** (which algorithms to use).
2. The server presents its **certificate** (its public key + identity, signed by a CA).
3. The client **verifies** the certificate (is it signed by a CA I trust? is it for this domain? not expired?).
4. They perform a **key exchange** (modern TLS uses Diffie-Hellman) to derive a shared symmetric key
   that an eavesdropper — even one recording everything — can't compute.
5. From here, everything is encrypted with that symmetric key.

### TLS 1.2 vs 1.3 — why 1.3 is better

- **1.2**: handshake takes **two round trips** before data flows; supports old, weak cipher options.
- **1.3**: handshake takes **one round trip** (0 in some resumption cases), and *only* strong ciphers
  are allowed — insecure options were removed from the spec.

**Why you care:** each round trip is a latency cost (recall file 02 — round trips are expensive over
distance). TLS 1.3 shaving a round trip off every new HTTPS connection is a real p99 improvement. Use 1.3.

---

## Certificates & the chain of trust

A **certificate** binds an identity (`example.com`) to a public key, and is **signed** by a
**Certificate Authority (CA)**. Your OS/browser ships with a list of trusted **root CAs**. Trust flows
in a chain:

```
Root CA (trusted by your OS)
   │ signs
   ▼
Intermediate CA
   │ signs
   ▼
Leaf certificate (example.com)  ← the one the server presents
```

When the server presents its leaf cert, your client walks *up* the chain: "who signed this leaf? an
intermediate. who signed that? a root I already trust. ✓". If any link is missing, expired, or
untrusted, validation fails — that's the dreaded `certificate verify failed`.

**Common real bugs:**
- **Expired cert** — the #1 outage cause; certs have a validity window (Let's Encrypt = 90 days).
- **Missing intermediate** — the server sent only the leaf; some clients can't build the chain. Serve the full chain.
- **Wrong domain** — the cert is for `example.com` but you hit `api.example.com` and it's not covered.

### Let's Encrypt & ACME — free automated certs

Historically certs cost money and were manually renewed (and forgotten → outages). **Let's Encrypt**
is a free CA; the **ACME protocol** automates issuance and renewal: you prove you control the domain
(via a DNS `TXT` record or an HTTP challenge — recall file 03's record types), and a cert is issued
and auto-renewed. Tools like Caddy, cert-manager (Kubernetes, topic 16), and certbot do this for you.

---

## SNI & ALPN — two handshake extensions you should know

Both solve real problems and both come up in load balancer config (file 07):

- **SNI (Server Name Indication):** one IP address can host many HTTPS sites. But the server needs to
  know *which* cert to present before it knows which site you want... chicken and egg. SNI fixes it:
  the client includes the hostname (`api.example.com`) in the very first handshake message, so the
  server picks the right cert. This is how virtual hosting works over HTTPS.
- **ALPN (Application-Layer Protocol Negotiation):** during the handshake, client and server agree on
  which application protocol to use — specifically **whether to speak HTTP/1.1 or HTTP/2** (file 05).
  This negotiation is why HTTP/2 "just works" over HTTPS without an extra round trip.

You'll literally see `ALPN, offering h2` in `curl -v --http2` output (planning Lab 5).

---

## mTLS — both sides prove identity

Normal TLS: the *server* proves its identity to the client (you verify example.com). **Mutual TLS
(mTLS):** the *client* also presents a certificate, so the server verifies the client too.

Where it's used: **service-to-service authentication** inside a system — service A and service B each
hold certs and verify each other, so only trusted services can talk. This is a building block of
**service meshes** (topic 12/16). Remember the term; you'll implement the concept later.

---

## TLS termination — a decision you'll actually make

"Where does TLS get decrypted?" is an architecture choice:

- **Terminate at the load balancer / reverse proxy:** the LB holds the cert, decrypts, and forwards
  **plain HTTP** to your backend over the private network. Simplest, offloads crypto from your app,
  centralises cert management. Most common. (Your nginx labs do this.)
- **End-to-end (re-encrypt):** the LB decrypts to inspect/route, then re-encrypts to the backend — or
  passes TLS straight through. Needed when the internal network isn't trusted, or for compliance.

**Trade-off:** terminating at the edge is simpler and faster but means traffic is plaintext on your
internal network (usually fine inside a private VPC); end-to-end is more secure but more complex and
adds crypto overhead on every hop.

> This connects to file 07 (L4 vs L7 load balancing): an L7 LB *must* terminate TLS to read HTTP; an
> L4 LB can pass encrypted bytes straight through without decrypting.

---

## Tools

- `openssl s_client -connect example.com:443` — see the cert chain, protocol version, cipher live (planning Lab 3).
- `mkcert` — mint a locally-trusted CA + cert for dev HTTPS without warnings (planning Lab 3).
- Browser devtools → Security tab — inspect the cert a site presented.

---

## Mental model

> TLS is a **sealed, tamper-evident envelope with a verified return address.** Encryption seals it
> (confidentiality), a checksum makes tampering obvious (integrity), and the CA-signed certificate is
> a notary vouching that the return address is genuine (authenticity). The handshake is the two
> parties agreeing on a one-time seal that only they can open.

---

## Check yourself

1. Name TLS's three guarantees and which mechanism provides each.
2. Why does TLS use *both* asymmetric and symmetric encryption instead of just one?
3. Why is TLS 1.3 faster than 1.2, in terms of file 02's round-trip cost?
4. Walk the chain of trust from a leaf cert to a root — what makes validation fail at each link?
5. What problem does SNI solve, and what does ALPN negotiate?
6. What is mTLS and where is it used?
7. Contrast terminating TLS at the load balancer vs end-to-end — the trade-off, and how it relates to L4 vs L7 (file 07).
