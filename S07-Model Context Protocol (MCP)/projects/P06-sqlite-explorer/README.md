# SQLite Explorer

Connects to a local SQLite DB. Resources: tables. Tools: run_query, list_tables, describe_table.

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
    "P06-sqlite-explorer": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P06-sqlite-explorer/server.py"]
    }
  }
}
```
