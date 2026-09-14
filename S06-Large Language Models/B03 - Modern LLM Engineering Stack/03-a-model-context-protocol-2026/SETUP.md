# Setup

## The one thing that will bite you

This folder has its **own** virtual environment, separate from the repository root
`.venv`. That is deliberate. The MCP v2 SDK pins `starlette>=1.6` and ships `httpx2`,
and mixing that into the root environment alongside LangChain, TensorFlow and the rest
is asking for a dependency fight you do not need while learning a protocol.

So: activate the local one, or call its interpreter by full path. If you have the root
`.venv` active in your shell, `uv pip install` will silently install into *that* one,
because `uv` honours `VIRTUAL_ENV` over the current directory.

## First-time setup

```bash
cd "S06-Large Language Models/B03 - Modern LLM Engineering Stack/03-a-model-context-protocol-2026"

# Create the local environment. --python 3.12 because that is what is installed;
# the project needs >=3.11.
uv venv --python 3.12

# Install. The VIRTUAL_ENV override is the safety belt described above.
VIRTUAL_ENV="$PWD/.venv" uv pip install --python "$PWD/.venv/bin/python" -e ".[dev]"
```

Then activate it for the rest of your session:

```bash
source .venv/bin/activate
```

## Check that it is right

```bash
python -c "
import importlib.metadata as md
for p in ('mcp', 'mcp-types', 'httpx2', 'pytest'):
    print(f'{p:12s} {md.version(p)}')
"
```

You want to see:

```text
mcp          2.1.1
mcp-types    2.1.1
httpx2       2.12.0
pytest       9.1.1
```

## Two package names that surprise people

**`mcp` and `mcp-types` are two distributions.** `mcp` is the SDK — servers, clients,
transports, the decorators. `mcp-types` is nothing but the wire types: every request,
result and notification shape, per protocol revision. You import from both:

```python
from mcp.server import MCPServer          # the SDK
from mcp_types import ToolAnnotations     # the wire types
```

Note the underscore. The distribution is `mcp-types`; the importable module is
`mcp_types`.

**`httpx` is `httpx2` here.** httpx 2.x is published on PyPI under a new distribution
name, `httpx2`, and the importable module is `httpx2` too. The MCP SDK depends on it. So
in the hand-rolled client scripts you will see:

```python
import httpx2 as httpx
```

That alias is only there so the code reads like every httpx snippet you have seen
elsewhere. If you `import httpx` you will get httpx 0.x if it happens to be installed,
or an `ImportError` if it is not — either way, not the library the SDK is using.

## Confirm the protocol revision the SDK speaks

Do this once. It is the fastest way to see that the 2026-07-28 revision genuinely
deleted things rather than merely deprecating them:

```bash
python -c "
from mcp_types.methods import CLIENT_REQUESTS, SERVER_REQUESTS
print('client -> server methods at 2026-07-28:')
for m in sorted(m for m, v in CLIENT_REQUESTS if v == '2026-07-28'):
    print('   ', m)
print()
print('server -> client requests at 2026-07-28:',
      sorted(m for m, v in SERVER_REQUESTS if v == '2026-07-28') or 'NONE')
"
```

Ten methods in one direction. Zero in the other. Topic 00 explains why that second line
is the most important line in the whole SDK.

## Running things

Every topic file is a standalone server you run directly:

```bash
python solved/t01_hello.py        # my version
python solutions/t01_hello.py     # yours
```

Each one binds `127.0.0.1:3010` and prints the exact `curl` commands to try against it.
Stop it with Ctrl-C.

The `curl/` scripts assume a server is already listening on 3010:

```bash
python solved/t01_hello.py &      # or use a second terminal
bash curl/01_discover.sh
```

Tests need no server at all — they drive the server's ASGI app in-process:

```bash
pytest
```

## Environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `CAFE_MCP_SECRET` | a fixed development key, with a warning on stderr | topic 07 onwards — signs the order token |
| `CAFE_MCP_INSTANCE` | `single` | topic 14 — the value each instance reports as `served_by` |
| `CAFE_MCP_PORT` | `3010` | every topic |

None of them are secret in any real sense. `CAFE_MCP_SECRET` exists so that topic 07 can
teach key handling honestly; the fallback deliberately shouts at you.

## Logging

Log to **stderr**, never stdout. Under the stdio transport, stdout carries protocol
messages and a stray `print()` corrupts the stream. Under HTTP it does not matter, but
the habit does — and MCP's own logging feature (`notifications/message`) is deprecated
as of 2026-07-28, so stderr and OpenTelemetry are what is left.

The teaching servers in `solved/` break this rule loudly and on purpose: they print to
stdout because you are reading the output, not piping it to a client. Every one of them
says so at the top.
