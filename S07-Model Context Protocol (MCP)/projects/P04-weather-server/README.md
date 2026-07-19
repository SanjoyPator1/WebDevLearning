# Weather Server

Real weather data using the Open-Meteo API (free, no key). Tools: current, forecast, history.

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
    "P04-weather-server": {
      "command": "python3",
      "args": ["/Users/yourname/path/to/P04-weather-server/server.py"]
    }
  }
}
```
