# Shared bits for every curl script in this folder. Source it, do not run it.
#
# Nothing here is MCP-specific magic — it is the boilerplate that makes the
# individual scripts short enough to read.

CAFE_HOST="${CAFE_HOST:-127.0.0.1}"
CAFE_PORT="${CAFE_MCP_PORT:-3010}"
CAFE_URL="http://${CAFE_HOST}:${CAFE_PORT}/mcp"
CAFE_VERSION="2026-07-28"

# Pretty-print JSON if python is around, otherwise pass it through untouched.
pp() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys
raw = sys.stdin.read()
# A streamable-HTTP response is either a plain JSON body or an SSE-framed one.
# Which you get depends on the headers you sent, so handle both.
if raw.lstrip().startswith(("event:", "data:", ":")):
    print("[SSE-framed response]")
    for line in raw.splitlines():
        if line.startswith("data: "):
            print(json.dumps(json.loads(line[6:]), indent=2))
        elif line.strip():
            print("  " + line)
else:
    try:
        print(json.dumps(json.loads(raw), indent=2))
    except Exception:
        print(raw)'
  else
    cat
  fi
}

banner() {
  echo "--------------------------------------------------------------------"
  echo "$1"
  echo "--------------------------------------------------------------------"
}

expect() {
  echo "EXPECT: $1"
  echo "--------------------------------------------------------------------"
}

# Build the `_meta` block every modern request must carry. Note it goes INSIDE
# `params`, never at the top level of the JSON-RPC envelope.
cafe_meta() {
  cat <<JSON
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "${CAFE_VERSION}",
      "io.modelcontextprotocol/clientInfo": {"name": "cafe-curl", "version": "1.0"},
      "io.modelcontextprotocol/clientCapabilities": {}
    }
JSON
}
