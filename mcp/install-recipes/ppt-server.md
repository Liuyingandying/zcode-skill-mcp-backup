# ppt-server

- Purpose: office-powerpoint-mcp-server via uvx
- Install: `uvx --from office-powerpoint-mcp-server --with mcp<2 ppt_mcp_server`
- Note: -

## Config template (secret-free)

```json
{"mcp": {"servers": {"ppt-server": {"command": "E:/conda/Scripts/uvx.exe", "args": ["--from", "office-powerpoint-mcp-server", "--with", "mcp<2", "ppt_mcp_server"]}}}}
```
