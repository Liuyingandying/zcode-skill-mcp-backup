# Plugin removal / reinstall notes (2026-10-02)

ZCode plugin identity = `<name>@<marketplace>`. Enable state lives in
`~/.zcode/cli/config.json` under `plugins.enabledPlugins`; bundled built-ins are
never deleted — they are disabled by an explicit `false` entry (or suppressed via
Settings → Plugin Management).

## Marketplace-installed plugins REMOVED (registration deleted + cache deleted)

| Plugin | Cache version | Reinstall |
|---|---|---|
| gitlab@zcode-plugins-official | 0.1.3 | Settings → Plugin Management → Discover (official marketplace) |
| lark-cli@zcode-plugins-official | 0.1.2 | same |
| tencent-meeting-cli@zcode-plugins-official | 0.1.3 | same |

Also removed: the materialized stubs `github@claude-plugins-official` /
`gitlab@claude-plugins-official` (0-component legacy copies superseded by the
zcode-plugins-official builds). The GitHub plugin that remains enabled is
`github@zcode-plugins-official` 0.1.2.

## Bundled built-ins DISABLED (files stay in the app bundle, only loading is off)

Set `<name>@zcode-plugins-official: false` (reverse: `true`) under
`plugins.enabledPlugins` in `~/.zcode/cli/config.json`:

- documents 0.1.7 (docx skill)
- pdf 0.1.7
- presentations 0.1.7 (pptx skill)
- spreadsheets 0.1.7 (xlsx skill)
- skill-creator 0.1.0
- plugin-creator 0.1.1
- zcode-guide 0.3.0 (6 configuration-diagnostic skills)

## Bundled built-ins KEPT enabled

- github@zcode-plugins-official 0.1.2 (marketplace-installed, kept — GitHub keep-set)
- browser-use 0.5.1, computer-use 0.6.3 (= bundled zcode-cua), node-repl-host 0.6.0
  (node_repl MCP host), image-search 0.1.1 (image_search MCP)
- dormant bundled packages left untouched: android-emulator, ios-simulator,
  restore-legacy-sessions, document-skills (cache re-materialized in place)
