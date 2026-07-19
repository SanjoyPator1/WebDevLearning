# Calculator

Multi-tool server: calculate, convert_units, format_number.

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
    "P03-calculator": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P03-calculator/server.py"]
    }
  }
}
```
