# Notes — Topic 01: Internet & HTTP

These are study notes for [planning/01_internet_and_http.md](../../planning/01_internet_and_http.md).
Read them in order; each builds on the last. They *teach* the concepts — the planning file is the
checklist, these are the explanations.

## Reading order

| File | Covers | Planning §|
|---|---|---|
| [01_layers_and_addressing.md](01_layers_and_addressing.md) | TCP/IP model, IP, ports, NAT, CIDR | 2.1, 2.2 |
| [02_tcp_and_udp.md](02_tcp_and_udp.md) | TCP handshake, connection states, keep-alive, UDP | 2.3 |
| [03_dns.md](03_dns.md) | Name resolution, record types, caching/TTL | 2.4 |
| [04_tls.md](04_tls.md) | Encryption, handshake, certificates, SNI/ALPN, mTLS | 2.5 |
| [05_http.md](05_http.md) | HTTP/1.1 semantics, HTTP/2, HTTP/3 & QUIC | 2.6–2.8 |
| [06_request_lifecycle.md](06_request_lifecycle.md) | Life of a request, timeout taxonomy | 2.9 |
| [07_proxies_and_load_balancers.md](07_proxies_and_load_balancers.md) | Proxies, L4/L7 LB, forwarded headers | 2.10 |

## How to use these notes

1. Read a file, then **do the matching lab** from the planning file — reading alone won't stick.
2. The **"Check yourself"** box at the end of each file is your gate. If you can't answer it, re-read.
3. Edit freely. Add your own findings from the labs, cross out anything you'd say differently. These
   become *your* notes.
4. When you finish all 7 + the labs + the mini-project, tick Topic 01 in [planning/00_index.md](../../planning/00_index.md).

## The one-sentence summary of this whole topic

> Before your FastAPI route function runs, a request travelled through DNS, TCP, TLS, a load
> balancer, and a reverse proxy — and knowing that path is what turns production debugging from
> guesswork into diagnosis.
