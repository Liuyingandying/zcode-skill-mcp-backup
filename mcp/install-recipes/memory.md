# memory

- Purpose: official MCP memory server (knowledge graph)
- Install: `npx -y @modelcontextprotocol/server-memory@2026.8.31`
- Note: -

## Config template (secret-free)

```json
{"mcp": {"servers": {"memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory@2026.8.31"],
  "env": {"MEMORY_FILE_PATH": "C:/Users/<you>/.zcode/memory/mcp-memory.jsonl"}}}}}
```
