# pinepaper

- Purpose: PinePaper Studio animation MCP (puppeteer)
- Install: `npx -y -p @pinepaper.studio/mcp-server -p puppeteer pinepaper-mcp`
- Note: -

## Config template (secret-free)

```json
{"mcp": {"servers": {"pinepaper": {"command": "npx", "args": ["-y", "-p", "@pinepaper.studio/mcp-server", "-p", "puppeteer", "pinepaper-mcp"],
  "env": {"PINEPAPER_EXECUTION_MODE": "puppeteer", "PUPPETEER_SKIP_DOWNLOAD": "1",
  "PUPPETEER_EXECUTABLE_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "PINEPAPER_EXPORT_DIR": "<your-export-dir>"}, "timeoutMs": 600000}}}}
```
