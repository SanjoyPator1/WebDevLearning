# 01 — Layers & Addressing

## Why start here

When you type `curl https://api.example.com/todos`, a dozen distinct systems cooperate to get bytes
there and back. They're organised in **layers**, each one doing a small job and handing off to the
next. If you don't know the layers, every networking problem looks like one undifferentiated blob.
Once you do, you can point at exactly which layer is misbehaving.

---

## The TCP/IP model (the one that matters)

There's a famous 7-layer OSI model, but in practice engineers use the 4-layer **TCP/IP model**.
Think of it as an onion — data goes *down* the layers on the sender, across the wire, and *up* the
layers on the receiver.

```
┌─────────────────────────────────────────────┐
│ Application   │ HTTP, DNS, TLS, gRPC, SSH     │  ← your API lives here
├─────────────────────────────────────────────┤
│ Transport     │ TCP, UDP                      │  ← "which program?" + reliability
├─────────────────────────────────────────────┤
│ Internet      │ IP (v4/v6), ICMP              │  ← "which machine?" + routing
├─────────────────────────────────────────────┤
│ Link          │ Ethernet, Wi-Fi              │  ← the physical hop to the next device
└─────────────────────────────────────────────┘
```

**Key idea — each layer only talks to the one below it.** HTTP doesn't know about Ethernet; it hands
a message to TCP, which hands a segment to IP, which hands a packet to the link layer. Each layer
*wraps* the data from above with its own header. This wrapping is called **encapsulation**.

### Encapsulation — what a packet actually contains

Picture sending "GET /todos". As it goes down the stack, each layer adds a header (like nesting envelopes):

```
[ Ethernet header [ IP header [ TCP header [ HTTP: GET /todos ] ] ] ]
   \_____________/  \________/  \_________/  \________________/
    "next device"   "which      "which       the actual payload
                     machine"    program +
                                 reliability"
```

On the receiving machine, each layer *peels off* its header and passes the rest up. The web server
only ever sees "GET /todos" — all the lower-layer machinery is invisible to it. This is exactly why
FastAPI hands you a clean request object: everything below the application layer was already handled.

> **OSI vs TCP/IP:** You'll hear "Layer 4" (transport/TCP) and "Layer 7" (application/HTTP) constantly
> — those numbers come from OSI. You don't need OSI's full 7 layers, but memorise **L4 = TCP/UDP**
> and **L7 = HTTP**, because load balancers are described as "L4" or "L7" and it changes what they can do (file 07).

---

## IP addresses — "which machine?"

Every device on a network has an **IP address**. Two versions exist:

- **IPv4**: 32 bits, written as four decimals — `93.184.216.34`. ~4.3 billion addresses, which we ran out of (hence NAT, below).
- **IPv6**: 128 bits, written in hex — `2606:2800:220:1:248:1893:25c8:1946`. Effectively unlimited.

### Public vs private addresses

Some IPv4 ranges are **private** — reserved for internal networks and never routed on the public
internet. You'll recognise these instantly once you know them:

| Range | CIDR | Where you see it |
|---|---|---|
| `10.0.0.0` – `10.255.255.255` | `10.0.0.0/8` | Cloud VPCs (topic 18), big internal nets |
| `172.16.0.0` – `172.31.255.255` | `172.16.0.0/12` | Docker's default bridge network (topic 15) |
| `192.168.0.0` – `192.168.255.255` | `192.168.0.0/16` | Home/office routers |
| `127.0.0.1` | `127.0.0.0/8` | **localhost** — your own machine |

Your laptop almost certainly has a private IP like `192.168.1.x`. So how does it reach a public
server? **NAT.**

### NAT — why the internet can't reach your laptop (but you can reach it)

**Network Address Translation** lets many devices with private IPs share one public IP (your
router's). When your laptop (`192.168.1.5`) sends a request out, the router rewrites the source
address to its own public IP and remembers the mapping. When the reply comes back, it rewrites it
back to your laptop.

```
Your laptop            Router (NAT)              Server
192.168.1.5:51000  →   203.0.113.7:44001    →   93.184.216.34:443
   (private)           (public, rewritten)       (public)
```

**Consequence:** an outside machine can't *initiate* a connection to your laptop — there's no
public address that points at it directly. This is why:
- You can browse the web but can't host a server on your laptop without port-forwarding.
- This same asymmetry drives why we need **public** load balancers / reverse proxies in front of
  backend servers (file 07) — the servers often sit in a private network (topic 18's VPC).

---

## Ports — "which program?"

An IP address gets you to the right *machine*. A **port** (a 16-bit number, 0–65535) gets you to the
right *program* on that machine. One server can run a web server on port 443, a database on 5432, and
SSH on 22 simultaneously — the port disambiguates.

- **Well-known ports**: 80 (HTTP), 443 (HTTPS), 22 (SSH), 5432 (Postgres), 6379 (Redis), 8000 (your dev FastAPI).
- A full connection is identified by a **4-tuple**: `(source IP, source port, dest IP, dest port)`.
  This is why one server can handle thousands of connections on port 443 — each client has a
  different source IP/port, so each tuple is unique.

### Ephemeral ports & "address already in use"

When your laptop makes an outbound connection, the OS assigns it a temporary **ephemeral port**
(e.g. `51000`) as the source. There's a limited range (~28,000 by default), which matters at scale:
a machine making huge numbers of outbound connections can exhaust them (relevant to `TIME_WAIT` in
file 02).

The error `Address already in use` when you restart your dev server means the port (e.g. 8000) is
still held by the previous process (or stuck in a closing TCP state) — the OS won't let two programs
bind the same port.

---

## CIDR notation — you'll need this a lot later

`10.0.0.0/16` is **CIDR** notation. The `/16` means "the first 16 bits are the network prefix; the
rest identify hosts within it."

- `/16` → first 16 bits fixed → `10.0.x.x` → **65,536** addresses
- `/24` → first 24 bits fixed → `10.0.0.x` → **256** addresses
- `/32` → all 32 bits fixed → exactly **one** address

Quick intuition: **bigger number = smaller network.** `/8` is huge, `/32` is a single host.

You'll design these when you build a VPC (topic 18) and when you read Kubernetes pod/service CIDRs
(topic 16). It's worth being able to eyeball "how many addresses is a /20?" (answer: 2^(32−20) = 4096).

---

## Mental model to keep

> **IP = which house. Port = which room. The 4-tuple = a specific conversation between two rooms in
> two houses.** NAT is the receptionist who lets everyone in the building share one street address.

---

## Check yourself

1. Data going "down the stack" gets a header added at each layer — what's that called, and what does the web server ultimately see?
2. Why can your laptop reach `example.com` but `example.com` can't start a connection to your laptop?
3. What does "L4 vs L7" refer to, and where do those numbers come from?
4. How many addresses are in a `/24`? In a `/16`?
5. What four things uniquely identify a single TCP connection?
6. You restart your FastAPI dev server and get "address already in use" — what does that mean is happening?

*(If any of these are shaky, re-read the matching section before moving to TCP.)*
