# GitHub Assistant

GitHub API integration. Resources: issues, PRs. Tools: create_issue, add_comment. Prompt: review-pr.

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
    "P05-github-assistant": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P05-github-assistant/server.py"]
    }
  }
}
```
