# zread

- Purpose: http MCP by z.ai for GitHub repo semantic reading
- Install: `None`
- Note: requires a z.ai API token (was stored in plaintext locally - rotate before reuse)

## Config template (secret-free)

```json
{"mcp": {"servers": {"zread": {"type": "http", "url": "https://api.z.ai/api/mcp/zread/mcp",
  "headers": {"Authorization": "Bearer ${ZREAD_TOKEN}"}, "timeoutMs": 60000}}}}
```
