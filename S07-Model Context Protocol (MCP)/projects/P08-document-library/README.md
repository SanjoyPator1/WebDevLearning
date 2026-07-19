# Document Library

Paginated document server. Cursor-based pagination + in-memory cache + file watching.

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
    "P08-document-library": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P08-document-library/server.py"]
    }
  }
}
```
