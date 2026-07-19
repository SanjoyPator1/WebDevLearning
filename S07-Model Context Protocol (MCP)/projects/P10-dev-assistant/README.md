# Dev Assistant

Developer tools for Cursor. Tools: run_tests, lint, git_log, git_diff, search_codebase.

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
    "P10-dev-assistant": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P10-dev-assistant/server.py"]
    }
  }
}
```
