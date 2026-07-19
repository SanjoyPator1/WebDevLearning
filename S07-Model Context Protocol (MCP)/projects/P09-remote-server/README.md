# Remote Server

HTTP+SSE remote server using FastAPI. Deployed to Railway. Bearer token auth.

## Status
- [ ] **Not started** — build this project when you reach it in the roadmap.

## How to Run

```bash
pip install -r requirements.txt
npx @modelcontextprotocol/inspector python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "P09-remote-server": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P09-remote-server/server.py"]
    }
  }
}
```
