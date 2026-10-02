# -*- coding: utf-8 -*-
"""Generate audit/REMOVE_SET.md + audit/ORIGINAL_PATH_MAP.md from MANIFEST.json."""
import json, os, shutil, hashlib, datetime

STAGE = r"D:\zcode-skill-mcp-backup"
WS = r"D:\glm生成计划\claude-video"
m = json.load(open(os.path.join(STAGE, "MANIFEST.json"), encoding="utf-8"))

def fh(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(65536), b""): h.update(c)
    except OSError: return "n/a"
    return h.hexdigest()[:16]

def dh(root):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        for f in sorted(fn):
            h.update(os.path.relpath(os.path.join(dp, f), root).encode())
            h.update(hashlib.sha256(open(os.path.join(dp, f), "rb").read()).hexdigest().encode())
    return h.hexdigest()[:16]

L = []
L.append("# REMOVE_SET.md\n")
L.append("> 本轮从 Z Code 环境真实删除的全部组件 ｜ 生成于 %s" % datetime.date.today().isoformat())
L.append("> SHA-256 为目录聚合摘要（相对路径+逐文件内容）或单文件前16位；完整 hash 见 MANIFEST.json\n")
L.append("## A. 用户级 Skills（26 个 .zcode + 2 个 .agents 中的 2 个 + 上轮 quarantine 5 个）\n")
L.append("| Name | 原路径 | 备份 | 大小 | SHA-256(目录) | 来源/版本 | License | 重新获取 |")
L.append("|---|---|---|---:|---|---|---|---|")
for it in m["skills"]:
    if it["name"] == "_commands (9 slash commands)": continue
    orig = it["original_path"]
    L.append("| %s | `%s` | `%s` | %.1f KB | %s | %s | %s | %s |" % (
        it["name"], orig, it["backup_path"], (it["size_bytes"] or 0) / 1024,
        (it["sha256_dir"] or "n/a")[:16], it["source"], it["license"], it["reinstall"]))
L.append("\n## B. Slash 命令（9 文件，随引用的 Skill 一并移除）\n")
L.append("| 原路径 | 备份 | SHA-256(目录) |")
L.append("|---|---|---|")
for it in m["skills"]:
    if it["name"].startswith("_commands"):
        L.append("| `%s` | `%s` | %s |" % (it["original_path"], it["backup_path"], it["sha256_dir"][:16]))
L.append("\n## C. MCP Server 注册（cli/config.json 中全部 10 项 → 清空 mcp.servers）\n")
L.append("| Name | 类型 | 配置模板/Recipe | Secret 处理 |")
L.append("|---|---|---|---|")
secretnote = {"zread": "Bearer → ${ZREAD_TOKEN}（原 token 明文本地存储，建议轮换）"}
for it in m["mcp"]:
    if "pinepaper" in it["name"].lower() and "project" in it["name"].lower():
        continue
    L.append("| %s | 配置注册项 | `%s` | %s |" % (it["name"], it["backup_path"],
              secretnote.get(it["name"], "无 secret")))
L.append("| Firefly_Animation_Test 项目级 pinepaper | 项目配置 | `mcp/local/project-pinepaper.example.json` | 无 secret |")
L.append("\n## D. 插件\n")
L.append("| Plugin | 处置 | 恢复方式 |")
L.append("|---|---|---|")
for p, how in [("gitlab", "Marketplace 重装（Settings→Plugin Management，官方 marketplace）"),
               ("lark-cli", "同上"),
               ("tencent-meeting-cli", "同上"),
               ("documents / pdf / presentations / spreadsheets（builtin 捆绑）", "配置停用（enabledPlugins=false），安装包文件不动；恢复=改回 true"),
               ("skill-creator / plugin-creator（builtin 捆绑）", "同上"),
               ("zcode-guide（builtin 捆绑）", "同上")]:
    L.append("| %s | 移除注册/停用 | %s |" % (p, how))
L.append("\n## E. 其他残留\n")
L.append("| Item | 原路径 | 处置 |")
L.append("|---|---|---|")
L.append("| 上一轮 quarantine | `~\\.zcode\\quarantine_20261002_133155\\`（5 个 Alvarmethod skill 影子 + document-skills 缓存物化） | skill 源码已备份至 skills/local/ 后删除；document-skills 属安装包物化 → 恢复原位而非删除 |")
L.append("| profile 切换器 | `~\\.zcode\\tools\\zcode_mcp_profile.ps1` | 已备份（mcp/local/）后删除 |")
L.append("| skill-sources/MathModelAgent | `~\\.zcode\\skill-sources\\MathModelAgent\\` | 上游克隆，未公开源码（上游 license 适用），目录删除 |")
L.append("| audit 探针脚本与结果 | `D:\\glm生成计划\\claude-video\\audit_work\\` | 结果与脚本已备份至 audit/probe-results 后删除 |")
L.append("| 上轮备份目录（含明文 token） | `~\\.zcode_backup_20261002_133155\\`、`~\\.zcode_backup_profile_switch\\` | 远端验证通过后删除（内含明文凭据，不宜长期留存） |")
L.append("| Firefly_Animation_Test 项目配置 | `D:\\glm生成计划\\Firefly_Animation_Test\\.zcode\\config.json` | 备份后删除 |")
L.append("\n**不删除**：ZCode 安装本体与内置捆绑包、`~\\.zcode\\v2\\`（session DB/credentials）、provider 配置、hooks（firefly_before_commit_check）、cli/config.json 的 subagents、`~\\.zcode\\memory\\mcp-memory.jsonl`（私有数据，MCP 注销后自然失活）、`C:\\Users\\FAJ\\plugins\\firefly-learning\\`（ZCode 环境之外的源项目）、E:\\Firefly_AI_MCP 全部 MCP 源码（仅注销注册，不删源码）、全部项目源码。\n")

open(os.path.join(STAGE, "audit", "REMOVE_SET.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L))
shutil.copy2(os.path.join(STAGE, "audit", "REMOVE_SET.md"), os.path.join(WS, "REMOVE_SET.md"))

# ORIGINAL_PATH_MAP
P = ["# ORIGINAL_PATH_MAP.md", "", "> 被移除组件：原位置 → 备份位置（或仅 manifest）对照表", ""]
P.append("## Skills（完整源码备份）")
P.append("")
P.append("| Original | Backup in this repo |")
P.append("|---|---|")
for it in m["skills"]:
    if it["name"] == "streamlit (developing-with-streamlit)":
        P.append("| %s | (manifest only) skills/manifests/streamlit.md |" % it["original_path"])
    else:
        P.append("| %s | %s |" % (it["original_path"], it["backup_path"]))
P.append("")
P.append("## MCP registrations")
P.append("")
P.append("| Original (all in ~/.zcode/cli/config.json mcp.servers) | Recipe |")
P.append("|---|---|")
for it in m["mcp"]:
    P.append("| %s | %s |" % (it["original_path"], it["backup_path"]))
P.append("| D:\\glm生成计划\\Firefly_Animation_Test\\.zcode\\config.json | mcp/local/project-pinepaper.example.json |")
P.append("")
P.append("## Misc")
P.append("")
for it in m["misc"]:
    P.append("| %s | %s |" % (it["original_path"], it["backup_path"]))
P.append("")
open(os.path.join(STAGE, "audit", "ORIGINAL_PATH_MAP.md"), "w", encoding="utf-8", newline="\n").write("\n".join(P))
shutil.copy2(os.path.join(STAGE, "audit", "ORIGINAL_PATH_MAP.md"), os.path.join(WS, "ORIGINAL_PATH_MAP.md"))
print("REMOVE_SET.md + ORIGINAL_PATH_MAP.md written (repo + workspace)")
