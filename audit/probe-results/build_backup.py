# -*- coding: utf-8 -*-
"""Stage the public GitHub backup: copy keep-worthy sources, build manifests,
compute SHA-256 inventory. Secret-free by construction (templates hand-written)."""
import os, re, json, shutil, hashlib, datetime

HOME = r"C:\Users\FAJ"
WS = r"D:\glm生成计划\claude-video"
STAGE = r"D:\zcode-skill-mcp-backup"
Q = os.path.join(HOME, ".zcode", "quarantine_20261002_133155", "agents-skills")
SKILLS = os.path.join(HOME, ".zcode", "skills")
ASKILLS = os.path.join(HOME, ".agents", "skills")
CMDS = os.path.join(HOME, ".zcode", "commands")
AW = os.path.join(WS, "audit_work")
VTMP = os.path.join(HOME, ".zcode", "tmp", "audit_validation")

OWN = ["2analysis-modeling","3coding-visual","4drawio","5writing","6verity",
       "mathmodel-data-tools","mmc-helper","modeling-reviewer","paper-miner",
       "paper-pipeline-fixer","paper-reviewer","competition-execution",
       "competition-manager","competition-radar","firefly-learning",
       "claude-motion-design","video-shotcraft","pinepaper-studio",
       "night-fiction-factory","literary-incident-response"]
MIT_3P = ["learn-profile","learn-verify","learn-visual","probe","teach"]
GEN_PROJECT = ["tju-academic-office-generator"]  # own, from .agents

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

def dirhash(root):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        for f in sorted(fn):
            h.update(os.path.relpath(os.path.join(dp, f), root).encode())
            h.update(sha(os.path.join(dp, f)).encode())
    return h.hexdigest()

def dsize(root):
    return sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(root) for f in fn)

def copydir(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".venv", "*.log", ".git"),
                    dirs_exist_ok=True)

manifest = {"generated": datetime.datetime.now().isoformat(), "skills": [], "mcp": [], "plugins": [], "misc": []}
os.makedirs(STAGE, exist_ok=True)
for d in ["skills/local","skills/manifests","mcp/local","mcp/manifests","mcp/install-recipes",
          "plugins/manifests","audit","audit/probe-results"]:
    os.makedirs(os.path.join(STAGE, d), exist_ok=True)

def reg(kind, name, orig, backup, size, hash_, source, version, license_, reason, reinstall):
    manifest[kind].append(dict(name=name, original_path=orig, backup_path=backup,
        size_bytes=size, sha256_dir=hash_, source=source, version=version,
        license=license_, removal_reason=reason, reinstall=reinstall))

# --- own skills (full source) ---
for n in OWN + GEN_PROJECT:
    src = os.path.join(SKILLS, n) if os.path.isdir(os.path.join(SKILLS, n)) else os.path.join(ASKILLS, n)
    dst = os.path.join(STAGE, "skills", "local", n)
    copydir(src, dst)
    reg("skills", n, src, f"skills/local/{n}", dsize(dst), dirhash(dst),
        "self-authored (local, AI-assisted)", datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(src,'SKILL.md'))).strftime('%Y-%m-%d'),
        "own content", "not needed by minimal env", "restore.ps1 skill " + n)

# --- MIT third-party skills (from last-round quarantine; full source + notice) ---
for n in MIT_3P:
    src = os.path.join(Q, n); dst = os.path.join(STAGE, "skills", "local", n)
    copydir(src, dst)
    reg("skills", n, rf"C:\Users\FAJ\.agents\skills\{n} (quarantined 2026-10-02)", f"skills/local/{n}",
        dsize(dst), dirhash(dst),
        "github.com/vasanthsreeram/Alvarmethod (MIT, verified via API 2026-10-02)",
        "installed 2026-08-29", "MIT (attribution kept in skills/local/THIRD-PARTY-NOTICE.md)",
        "minimal-env decision", "restore.ps1 skill " + n)

with open(os.path.join(STAGE, "skills", "local", "THIRD-PARTY-NOTICE.md"), "w", encoding="utf-8") as f:
    f.write("""# Third-Party Skill Notices

## Alvarmethod skills (learn-profile, learn-verify, learn-visual, probe, teach)

- Source: https://github.com/vasanthsreeram/Alvarmethod
- License: MIT (verified via GitHub API on 2026-10-02)
- Installed locally: 2026-08-29 (per ~/.agents/.skill-lock.json)
- These directories are redistributed under the terms of the MIT license of the upstream project.
- Upstream copyright remains with the original author.

## official-document-writing

- Source: https://github.com/KaguraNanaga/official-document-writing-skill v1.0 (commit e76a6f5)
- License: MIT — original LICENSE file kept inside the skill directory.
- NOTE: this skill is NOT part of the removal set; it remains in the live environment.
  It is documented here because the tju adapter redistributes/references it.
""")

# --- manifest-only (license unclear) ---
streamlit_src = os.path.join(SKILLS, "streamlit")
manifest["skills"].append(dict(name="streamlit (developing-with-streamlit)",
    original_path=streamlit_src, backup_path="skills/manifests/streamlit.md",
    size_bytes=os.path.getsize(os.path.join(streamlit_src, "SKILL.md")),
    sha256_dir=sha(os.path.join(streamlit_src, "SKILL.md")),
    source="unverified (style suggests anthropics/skills; that repo carries NO license)",
    version="n/a", license="UNCLEAR -> source not redistributed (metadata only)",
    removal_reason="third-party, license unclear", reinstall="see skills/manifests/streamlit.md"))

# --- commands ---
cdst = os.path.join(STAGE, "skills", "local", "_commands")
os.makedirs(cdst, exist_ok=True)
for f in os.listdir(CMDS):
    shutil.copy2(os.path.join(CMDS, f), os.path.join(cdst, f))
reg("skills", "_commands (9 slash commands)", CMDS, "skills/local/_commands",
    dsize(cdst), dirhash(cdst), "self-authored", "2026-09",
    "own content", "reference removed skills / project-specific workflows", "restore.ps1 skill _commands")

# --- skill-sources/MathModelAgent (3rd-party clone, manifest only) ---
ss = os.path.join(HOME, ".zcode", "skill-sources", "MathModelAgent")
manifest["misc"].append(dict(name="skill-sources/MathModelAgent", original_path=ss,
    backup_path="audit/REMOVE_SET.md#mathmodelagent", size_bytes=dsize(ss), sha256_dir=dirhash(ss),
    source="cloned repo (has own LICENSE in dir)", version="n/a", license="upstream repo license — not redistributed",
    removal_reason="historical source clone, unused", reinstall="re-clone from upstream if needed"))

# --- MCP recipes (hand-written, secret-free) ---
RECIPES = {
 "zread": ("http MCP by z.ai for GitHub repo semantic reading", None,
   '{"mcp": {"servers": {"zread": {"type": "http", "url": "https://api.z.ai/api/mcp/zread/mcp",\n  "headers": {"Authorization": "Bearer ${ZREAD_TOKEN}"}, "timeoutMs": 60000}}}}',
   "requires a z.ai API token (was stored in plaintext locally - rotate before reuse)"),
 "memory": ("official MCP memory server (knowledge graph)", "npx -y @modelcontextprotocol/server-memory@2026.8.31",
   '{"mcp": {"servers": {"memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory@2026.8.31"],\n  "env": {"MEMORY_FILE_PATH": "C:/Users/<you>/.zcode/memory/mcp-memory.jsonl"}}}}}', None),
 "context7": ("Upstash Context7 library docs MCP", "npx -y @upstash/context7-mcp@4.1.1",
   '{"mcp": {"servers": {"context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp@4.1.1"]}}}}', None),
 "word-document-server": ("office-word-mcp-server via uvx", "uvx --from office-word-mcp-server word_mcp_server",
   '{"mcp": {"servers": {"word-document-server": {"command": "E:/conda/Scripts/uvx.exe",\n  "args": ["--from", "office-word-mcp-server", "word_mcp_server"]}}}}', None),
 "ppt-server": ("office-powerpoint-mcp-server via uvx", "uvx --from office-powerpoint-mcp-server --with mcp<2 ppt_mcp_server",
   '{"mcp": {"servers": {"ppt-server": {"command": "E:/conda/Scripts/uvx.exe", "args": ["--from", "office-powerpoint-mcp-server", "--with", "mcp<2", "ppt_mcp_server"]}}}}', None),
 "pandoc": ("mcp-pandoc via uvx", "uvx mcp-pandoc",
   '{"mcp": {"servers": {"pandoc": {"command": "E:/conda/Scripts/uvx.exe", "args": ["mcp-pandoc"]}}}}', None),
 "pinepaper": ("PinePaper Studio animation MCP (puppeteer)", "npx -y -p @pinepaper.studio/mcp-server -p puppeteer pinepaper-mcp",
   '{"mcp": {"servers": {"pinepaper": {"command": "npx", "args": ["-y", "-p", "@pinepaper.studio/mcp-server", "-p", "puppeteer", "pinepaper-mcp"],\n  "env": {"PINEPAPER_EXECUTION_MODE": "puppeteer", "PUPPETEER_SKIP_DOWNLOAD": "1",\n  "PUPPETEER_EXECUTABLE_PATH": "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",\n  "PINEPAPER_EXPORT_DIR": "<your-export-dir>"}, "timeoutMs": 600000}}}}', None),
 "research-knowledge": ("self-authored research MCP (local venv)", "local source at E:\\Firefly_AI_MCP\\research_mcp (kept on disk, source not deleted)",
   '{"mcp": {"servers": {"research-knowledge": {"command": "E:\\\\Firefly_AI_MCP\\\\research_mcp\\\\.venv\\\\Scripts\\\\python.exe",\n  "args": ["E:\\\\Firefly_AI_MCP\\\\research_mcp\\\\server.py"]}}}}', None),
 "academic-office": ("self-authored TJU academic docx MCP", "local source at E:\\Firefly_AI_MCP\\academic_office_mcp (kept on disk)",
   '{"mcp": {"servers": {"academic-office": {"command": "E:/conda/python.exe", "args": ["E:/Firefly_AI_MCP/academic_office_mcp/server.py"]}}}}', None),
 "teach-mcp": ("self-authored teaching MCP", "local source at E:\\Firefly_AI_MCP\\teach_mcp (kept on disk)",
   '{"mcp": {"servers": {"teach-mcp": {"command": "E:/conda/python.exe", "args": ["E:\\\\Firefly_AI_Pet\\\\tools\\\\teach_mcp_provider_launcher.py", "E:\\\\Firefly_AI_MCP\\\\teach_mcp\\\\server.py"]}}}}', None),
}
for name, (desc, install, cfgtpl, note) in RECIPES.items():
    with open(os.path.join(STAGE, "mcp", "install-recipes", f"{name}.md"), "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n- Purpose: {desc}\n- Install: `{install}`\n- Note: {note or '-'}\n\n## Config template (secret-free)\n\n```json\n{cfgtpl}\n```\n")
    manifest["mcp"].append(dict(name=name, original_path=f"C:\\Users\\FAJ\\.zcode\\cli\\config.json mcp.servers.{name}",
        backup_path=f"mcp/install-recipes/{name}.md", size_bytes=None, sha256_dir=None,
        source=desc, version="n/a", license="recipe only (no source redistributed)",
        removal_reason="minimal-env decision (not builtin / not writing / not github)",
        reinstall="merge config template into ~/.zcode/cli/config.json mcp.servers; see recipe"))

with open(os.path.join(STAGE, "mcp", "local", "config-mcp-servers.template.json"), "w", encoding="utf-8") as f:
    f.write("// Pre-removal full MCP server set (2026-10-02). Secrets replaced by env placeholders.\n"
            "// Paste entries back under mcp.servers in ~/.zcode/cli/config.json as needed.\n"
            "// ${ZREAD_TOKEN} must be provided by you; rotate the old token (it was stored in plaintext).\n" +
            "\n".join(json.loads(json.dumps(c)) and "```" and "" for c in []) )
# write real combined template
import textwrap
tpl = {"mcp": {"servers": {
    "zread": {"type": "http", "url": "https://api.z.ai/api/mcp/zread/mcp",
              "headers": {"Authorization": "Bearer ${ZREAD_TOKEN}"}, "timeoutMs": 60000},
    "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory@2026.8.31"],
               "env": {"MEMORY_FILE_PATH": "C:/Users/<you>/.zcode/memory/mcp-memory.jsonl"}},
    "context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp@4.1.1"]},
    "word-document-server": {"command": "E:/conda/Scripts/uvx.exe", "args": ["--from", "office-word-mcp-server", "word_mcp_server"]},
    "ppt-server": {"command": "E:/conda/Scripts/uvx.exe", "args": ["--from", "office-powerpoint-mcp-server", "--with", "mcp<2", "ppt_mcp_server"]},
    "pandoc": {"command": "E:/conda/Scripts/uvx.exe", "args": ["mcp-pandoc"]},
    "pinepaper": {"command": "npx", "args": ["-y", "-p", "@pinepaper.studio/mcp-server", "-p", "puppeteer", "pinepaper-mcp"],
                  "env": {"PINEPAPER_EXECUTION_MODE": "puppeteer", "PUPPETEER_SKIP_DOWNLOAD": "1",
                          "PUPPETEER_EXECUTABLE_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                          "PINEPAPER_EXPORT_DIR": "<your-export-dir>"}, "timeoutMs": 600000},
    "research-knowledge": {"command": "E:\\Firefly_AI_MCP\\research_mcp\\.venv\\Scripts\\python.exe", "args": ["E:\\Firefly_AI_MCP\\research_mcp\\server.py"]},
    "academic-office": {"command": "E:/conda/python.exe", "args": ["E:/Firefly_AI_MCP/academic_office_mcp/server.py"]},
    "teach-mcp": {"command": "E:/conda/python.exe", "args": ["E:\\Firefly_AI_Pet\\tools\\teach_mcp_provider_launcher.py", "E:\\Firefly_AI_MCP\\teach_mcp\\server.py"]}
}}}
json.dump(tpl, open(os.path.join(STAGE, "mcp", "local", "config-mcp-servers.template.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# project-scoped pinepaper example (no secrets)
shutil.copy2(r"D:\glm生成计划\Firefly_Animation_Test\.zcode\config.json",
             os.path.join(STAGE, "mcp", "local", "project-pinepaper.example.json"))
manifest["mcp"].append(dict(name="Firefly_Animation_Test project pinepaper config", 
    original_path=r"D:\glm生成计划\Firefly_Animation_Test\.zcode\config.json",
    backup_path="mcp/local/project-pinepaper.example.json", size_bytes=None, sha256_dir=None,
    source="self config", version="n/a", license="own", removal_reason="minimal-env decision",
    reinstall="copy to <project>/.zcode/config.json"))

# profile switcher + audit scripts
shutil.copy2(os.path.join(HOME, ".zcode", "tools", "zcode_mcp_profile.ps1"),
             os.path.join(STAGE, "mcp", "local", "zcode_mcp_profile.ps1"))
manifest["misc"].append(dict(name="zcode_mcp_profile.ps1", original_path=rf"{HOME}\.zcode\tools\zcode_mcp_profile.ps1",
    backup_path="mcp/local/zcode_mcp_profile.ps1", size_bytes=None, sha256_dir=None, source="self-authored",
    version="1.0", license="own", removal_reason="managed only now-removed MCPs", reinstall="copy back"))
for f in os.listdir(AW):
    shutil.copy2(os.path.join(AW, f), os.path.join(STAGE, "audit", "probe-results", f))
for f in os.listdir(VTMP):
    shutil.copy2(os.path.join(VTMP, f), os.path.join(STAGE, "audit", "probe-results", f))
manifest["misc"].append(dict(name="audit/probe-results", original_path=AW + " and " + VTMP,
    backup_path="audit/probe-results", size_bytes=dsize(os.path.join(STAGE, "audit", "probe-results")),
    sha256_dir=dirhash(os.path.join(STAGE, "audit", "probe-results")), source="self-generated",
    version="n/a", license="own", removal_reason="temp audit scripts", reinstall="n/a"))

json.dump(manifest, open(os.path.join(STAGE, "MANIFEST.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n_items = sum(len(v) for v in manifest.values())
print(f"STAGED: {n_items} items; skills/local={len(os.listdir(os.path.join(STAGE,'skills','local')))} entries; "
      f"total={dsize(STAGE)/1024:.0f} KB")
