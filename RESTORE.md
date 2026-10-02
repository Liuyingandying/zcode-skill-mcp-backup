# RESTORE.md

Restore components **one at a time**, only when needed. Nothing here auto-installs.

## Skills

```powershell
# see everything available
.\restore.ps1 list

# restore one skill (copies to ~/.zcode/skills/<name>; refuses to overwrite)
.\restore.ps1 skill 5writing
.\restore.ps1 skill mmc-helper
```

- Skills land in `~\.zcode\skills\<name>\`. Restart your Z Code session afterwards.
- `learn-profile / learn-verify / learn-visual / probe / teach` originally lived in
  `~\.agents\skills\` — restore with `.\restore.ps1 skill <name> -Scope agents` if you
  want them back at their original location (either scope works; `.zcode` wins on
  name clashes).
- `_commands` restores the archived slash-command `.md` files to `~\.zcode\commands\`.
  Note: several commands reference skills that are NOT restored by default
  (competition-*, tju-academic-office-generator); restore those first or the
  commands will route to nothing.

## MCP servers

```powershell
.\restore.ps1 mcp context7     # prints the config recipe
```

The recipe shows the exact JSON to paste under `mcp.servers` in
`~\.zcode\cli\config.json`. A full sanitized pre-removal snapshot (all 10 servers)
is in `mcp/local/config-mcp-servers.template.json`.

**Secrets are not restored.** The zread server needs `Authorization: Bearer <your-token>`
— the old token was stored in plaintext and should be considered compromised: rotate it
at z.ai, then export it as `ZREAD_TOKEN` rather than hardcoding it.

Self-authored MCP sources were **not deleted** from this machine
(`E:\Firefly_AI_MCP\research_mcp`, `E:\Firefly_AI_MCP\academic_office_mcp`,
`E:\Firefly_AI_MCP\teach_mcp`) — only their Z Code registration was removed.
Re-register with the recipes; the code is still on disk.

## Plugins

- `gitlab`, `lark-cli`, `tencent-meeting-cli`: marketplace-installed → reinstall from
  **Settings → Plugin Management → Discover** (official marketplace `zcode-plugins-official`).
- Bundled built-ins (documents, pdf, presentations, spreadsheets, skill-creator,
  plugin-creator, zcode-guide): never deleted, only disabled. Re-enable by setting
  `<plugin>@zcode-plugins-official: true` under `plugins.enabledPlugins` in
  `~\.zcode\cli\config.json` (or Settings → Plugin Management).

## Project-scoped example

`mcp/local/project-pinepaper.example.json` shows how pinepaper was scoped to the
`Firefly_Animation_Test` project: copy it to `<project>\.zcode\config.json`.

## Profile switcher

`mcp/local/zcode_mcp_profile.ps1` was the previous on/off switcher for the user-level
MCP set. With all user MCPs removed it has nothing to manage; copy it back only if you
re-register several servers.
