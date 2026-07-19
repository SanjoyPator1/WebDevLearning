# Filesystem Manager

File manager scoped to a safe directory. Tools: read, write, move, search files.

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
    "P07-filesystem-manager": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P07-filesystem-manager/server.py"]
    }
  }
}
```
