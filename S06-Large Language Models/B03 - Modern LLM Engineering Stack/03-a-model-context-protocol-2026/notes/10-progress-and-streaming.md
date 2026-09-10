# Progress on the Response Stream

## Table of contents

- [One sentence](#one-sentence)
- [Where this sits](#where-this-sits)
- [The problem this topic solves](#the-problem-this-topic-solves)
- [Layer 1 — The intuition](#layer-1-the-intuition)
- [Layer 2 — The mechanics](#layer-2-the-mechanics)
  - [Opting in: `progressToken`](#opting-in-progresstoken)
  - [What the wire actually looks like](#what-the-wire-actually-looks-like)
  - [The code](#the-code)
  - [Progress counts across every line, not reset per drink](#progress-counts-across-every-line-not-reset-per-drink)
  - [What "silent" actually costs: the work still happens](#what-silent-actually-costs-the-work-still-happens)
  - [The removal: SSE resumability is gone](#the-removal-sse-resumability-is-gone)
  - [Proof: killing a connection genuinely cancels the work](#proof-killing-a-connection-genuinely-cancels-the-work)
  - [Proof: `Last-Event-ID` does nothing](#proof-last-event-id-does-nothing)
- [Layer 3 — Dry-run: one brew, second by second](#layer-3-dry-run-one-brew-second-by-second)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Connection forward](#connection-forward)

## One sentence

`report_progress` sends a notification on the *same* response stream the caller is already
waiting on, and it only does anything at all if the caller asked for it by sending a
`progressToken` — otherwise the identical work happens in identical silence.

## Where this sits

Every tool built so far has answered instantly. `brew` is the first one that legitimately
takes real seconds, and it is where the word "streamable" in "Streamable HTTP" finally
means something. Every earlier topic could have run over plain HTTP with no meaningful
loss; this one could not.

## The problem this topic solves

A customer has paid (topic 09) and wants their coffee. Brewing two drinks takes a few real
seconds. Say nothing for those seconds and the customer — or the model relaying to them —
is staring at a call that looks hung. Say something, and you need a channel to say it on,
given that MRTR already removed the one kind of message a server used to be able to push
to a client. Progress is not part of MRTR. It solves a related but different problem: not
"I need an answer before I can finish" (that is `input_required`), but "I am still working,
here is where I am."

## Layer 1 — The intuition

A pizza-tracking app does not text you once, at the end, saying "delivered." It says
"order placed," then "in the oven," then "out for delivery," each one landing on the same
notification channel you already subscribed to — you did not open a new app for each
update. `report_progress` is that same channel, reused for exactly this purpose: several
small updates riding the *one* connection already open for the request that needs them.

## Layer 2 — The mechanics

### Opting in: `progressToken`

Nothing about `brew`'s code checks whether progress is wanted. It just calls
`report_progress` in a loop. Whether that produces anything on the wire is decided
entirely by the **client**, before the tool ever runs, by including a `progressToken` in
the request's `_meta`:

```json
"_meta": {
  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
  "io.modelcontextprotocol/clientCapabilities": {},
  "progressToken": "cafe-progress-demo"
}
```

Any value you choose. It comes back unchanged on every notification, which is how a
client juggling several in-flight calls tells their progress apart.

### What the wire actually looks like

With a `progressToken` present, the response's `content-type` switches from
`application/json` to `text/event-stream`, and the notifications arrive as their own SSE
events, ahead of the final result on that same stream:

```text
event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"cafe-progress-demo","progress":1,"total":10,"message":"grinding — Latte (L)"}}

event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"cafe-progress-demo","progress":2,"total":10,"message":"tamping — Latte (L)"}}

... six more, one every ~0.8s ...

event: message
data: {"jsonrpc":"2.0","id":1000,"result":{"resultType":"complete","structuredContent":{"ready":true,...}}}
```

One POST. One response. Eleven SSE events — ten `notifications/progress`, then the actual
`tools/call` result as the last event, carrying the `id` the client originally sent. No
second connection was opened for the notifications; they are frames on the response body
of the request that asked for them, which is the entire meaning of "streamable" in
Streamable HTTP.

### The code

```python
total_steps = len(priced_lines) * len(BREW_STEPS)
done = 0

for line in priced_lines:
    for step in BREW_STEPS:
        done += 1
        message = f"{step} — {line.name} ({line.size})"
        await ctx.report_progress(progress=done, total=total_steps, message=message)
        await anyio.sleep(STEP_DELAY_S)
```

`ctx.report_progress(progress, total, message)` — all three fields are exactly what
appeared on the wire above. `progress` and `total` let a client render a bar or a
percentage; `message` is the human-readable label. None of the three is required to be
anything in particular — `total` can even be `None` for a job whose length you cannot
predict — but giving a client an honest `total` is what lets it show something better than
a spinner.

### Progress counts across every line, not reset per drink

`done` is a single counter across the whole order, not reset to zero for each new line.
Verified: a two-line order (latte, then espresso) produces progress `1, 2, ..., 10`, never
`1, 2, 3, 4, 5, 1, 2, 3, 4, 5`. A client rendering one progress bar for the whole call needs
monotonic progress across the entire job; restarting the count partway through would make
the bar visibly jump backward.

### What "silent" actually costs: the work still happens

Run the identical call with no `progressToken`:

```bash
time bash curl/10_brew_no_progress_token.sh <order token>
```

```text
real  0m8.032s
```

Eight seconds of silence, then one plain JSON body. The server executed the exact same ten
`await ctx.report_progress(...)` calls it always does — they simply produced nothing to
send, because there was no token to attach a notification to. This is worth sitting with:
progress reporting costs the tool author nothing to add and nothing to skip; the decision
of whether it is *visible* belongs entirely to whoever is calling, not to whoever wrote the
tool.

### The removal: SSE resumability is gone

Every event above arrived with no `id:` field — only `event: message` and `data: ...`.
That is not an oversight in this café's server; it is the 2026-07-28 revision itself. The
`Last-Event-ID` header, and the SSE event IDs a client would have needed to say "resume
from event 7," were both removed from Streamable HTTP at this revision. A broken response
stream loses the in-flight request outright. The only recovery is reissuing the whole call
as a **new** request, with a new JSON-RPC id.

### Proof: killing a connection genuinely cancels the work

This is not merely "the client stops seeing updates" — the work itself stops. Start
`t10_progress.py` in one terminal, watch its own log, and in another:

```bash
bash curl/10_interrupt_brew.sh <order token>
```

which sends `--max-time 2` against a job that needs about eight seconds. The **server's**
own terminal — not curl's output — shows:

```text
[server] brew step 1/10: grinding — Latte (L)
[server] brew step 2/10: tamping — Latte (L)
[server] brew step 3/10: extracting — Latte (L)
```

and then nothing. No step 4. No "brew COMPLETE." The coroutine backing that request was
cancelled the moment the connection died, not merely disconnected from while continuing to
run unseen. The drink that was mid-extraction never finishes being brewed, and there is no
partial credit — the only way forward is calling `brew` again from scratch.

This matters for anything with a real side effect longer than an HTTP round trip:
statelessness plus no resumability means a slow tool must be safe to abandon partway,
because abandonment is a normal, expected outcome, not an edge case.

### Proof: `Last-Event-ID` does nothing

Send it anyway, exactly as a pre-2026 client resuming a stream would have:

```bash
curl ... -H 'Last-Event-ID: 5' ...
```

```text
event: message
data: {..."progress":1,"total":10,"message":"grinding — Latte (L)"...}
```

Progress starts at **1**, not wherever event 5 might have implied. The header is not
rejected, not validated, not read at all — it is simply irrelevant, because there is no
event history anywhere to resume from. The brew restarts completely, exactly as if the
header had never been sent.

## Layer 3 — Dry-run: one brew, second by second

A two-line order — one latte, one espresso — reaches `brew`, and the client sent a
`progressToken`.

```text
t=0.0s   done=1/10   report_progress("grinding — Latte (L)")     -> SSE event 1 sent
t=0.8s   done=2/10   report_progress("tamping — Latte (L)")      -> SSE event 2 sent
t=1.6s   done=3/10   report_progress("extracting — Latte (L)")   -> SSE event 3 sent
t=2.4s   done=4/10   report_progress("steaming milk — Latte (L)")-> SSE event 4 sent
t=3.2s   done=5/10   report_progress("pouring — Latte (L)")      -> SSE event 5 sent
t=4.0s   done=6/10   report_progress("grinding — Espresso (S)")  -> SSE event 6 sent
t=4.8s   done=7/10   report_progress("tamping — Espresso (S)")   -> SSE event 7 sent
t=5.6s   done=8/10   report_progress("extracting — Espresso (S)")-> SSE event 8 sent
t=6.4s   done=9/10   report_progress("steaming milk — Espresso (S)")-> SSE event 9 sent
t=7.2s   done=10/10  report_progress("pouring — Espresso (S)")   -> SSE event 10 sent
t=8.0s   return BrewResult(ready=True, lines=[...])              -> final result sent
```

Eleven writes to one open response body, across eight seconds, on the connection the
client opened at `t=0`. Kill that connection at `t=2.0s` and the trace stops dead after
event 2 or 3 — nothing at `t=2.4s` onward ever runs.

## Gotchas

**Progress is opt-in by the client, not the tool.** A tool author cannot force progress to
be visible, and cannot suppress it either — both are decided by whether the caller sent a
`progressToken`.

**No `progressToken` does not mean no work.** It means no *visibility* into work that
still fully happens, on the same timeline, every time.

**A dropped connection cancels the coroutine.** Design any long-running tool assuming
abandonment is routine, not exceptional — there is no "it kept running in the background
and you can check back later" without building that yourself (topics 11 onward touch
adjacent ideas, but plain `report_progress` does not give you this for free).

**`Last-Event-ID` is not validated — it is ignored.** Sending it produces no error and no
special behavior. There is no partial-resume path to accidentally rely on.

**Progress counts should be monotonic across the whole call**, not reset per sub-item, if
you want a client's single progress bar to make sense.

**A retry after a dropped connection is a brand-new JSON-RPC request**, with a new `id`.
Nothing links it to the abandoned one except whatever your own tool logic — reloading the
same order token, for instance — makes true by coincidence of shared arguments.

## Your turn

`solutions/t10_progress.py`, four code TODOs plus one experiment. The experiment is the
one worth taking seriously: **predict**, before running `curl/10_interrupt_brew.sh`,
exactly which step number your server's own log will stop at, and whether "brew COMPLETE"
will ever print for that interrupted call. Then run it, watching the server terminal, and
check your prediction against reality.

## Connection forward

Progress notifications ride the response of the request that needed them — they never
needed a session, and they are gone the moment that one response ends. Topic 11 asks about
notifications with a longer life: what happens when a client wants to know *whenever* the
menu changes, not just during one call in progress? That is `subscriptions/listen`, and it
is the one place in this entire folder where statelessness genuinely runs out of road —
nine of the ten RPCs you have built so far scale across any number of server instances
with zero shared state; this tenth one cannot, and knowing precisely why is the last piece
of the puzzle this ladder has been building toward.

Does this make sense? Want me to go deeper on any part — why progress is opt-in per
request rather than a server-wide setting, what cancellation actually looks like from
inside the coroutine, or why resumability was worth removing even though it costs
something real?
