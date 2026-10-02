# zcode-skill-mcp-backup

## Purpose

Archived optional Z Code skills, MCP configurations and restoration manifests.

This is **not** a Z Code distribution. It is the personal archive of components that were
removed from one user's Z Code environment on 2026-10-02 during a deliberate slim-down
(keep-set: application-writing skills + GitHub integration + Z Code built-ins only).
Everything here was working locally right before removal; restore only what you actually need.

## Contents

```
skills/local/            full source of archived custom skills (own + permissively licensed)
skills/local/THIRD-PARTY-NOTICE.md   licenses & provenance for third-party skills
skills/manifests/        metadata-only records for skills whose license is unclear
mcp/install-recipes/     per-server re-install recipes + sanitized config templates
mcp/local/               sanitized MCP config template (secrets -> env placeholders),
                         project-scoped example, profile switcher script
plugins/manifests/       plugin removal/reinstall notes
audit/REMOVE_SET.md      what was removed, with paths and SHA-256
audit/ORIGINAL_PATH_MAP.md   original location -> backup location map
audit/probe-results/     health-check scripts and probe outputs used in the audit
MANIFEST.json            machine-readable inventory (paths, sizes, hashes, licenses)
```

## Security

- **All secrets removed.** No `config.json` originals, tokens, API keys, cookies or
  credentials are committed. One plaintext token found during audit was replaced by
  `${ZREAD_TOKEN}` placeholders; rotate that token before reuse.
- Scanned with gitleaks 8.30.1 (0 findings after redaction) plus a keyword/entropy
  second pass (0 findings). Two gitleaks hits were manually verified as environment
  variable *names* and are recorded in `.gitleaksignore`.
- Media assets of third-party skills (BGM/SFX, textures) are **not** included — their
  licensing is separate from the code licenses.

## Restore

Do **not** restore everything. Restore single components on demand:

```powershell
.\restore.ps1 list                 # show what is available
.\restore.ps1 skill <name>         # copy one skill back to ~/.zcode/skills/<name>
.\restore.ps1 mcp <name>           # print the MCP recipe (config template) to paste
```

`restore.ps1` never overwrites an existing component and never restores secrets —
for MCPs that need a token you must supply it yourself via environment variable.

Details: [RESTORE.md](RESTORE.md) · full inventory: [MANIFEST.json](MANIFEST.json) ·
what was removed and why: [audit/REMOVE_SET.md](audit/REMOVE_SET.md)

## Disclaimer

Third-party components belong to their authors. Where a permissive license (MIT /
Apache-2.0) allows redistribution, the source is archived here together with its
license notice. Where licensing was unclear, **only installation metadata and source
links are kept — no source code is republished.**
