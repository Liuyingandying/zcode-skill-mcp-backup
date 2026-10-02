# word-document-server

- Purpose: office-word-mcp-server via uvx
- Install: `uvx --from office-word-mcp-server word_mcp_server`
- Note: -

## Config template (secret-free)

```json
{"mcp": {"servers": {"word-document-server": {"command": "E:/conda/Scripts/uvx.exe",
  "args": ["--from", "office-word-mcp-server", "word_mcp_server"]}}}}
```
