# MANIFEST.md（人读版）

> 机器可读全量清单见 [MANIFEST.json](MANIFEST.json)（含逐项 SHA-256、字节数、来源、License）
> 生成于 2026-10-02，对应 ZCode 3.14.x（Windows）用户环境

## 归档内容总览

| 类别 | 数量 | 位置 | 说明 |
|---|---:|---|---|
| 自研 Skills（完整源码） | 20 | `skills/local/` | 数学建模管线×10、比赛×3、firefly-learning、claude-motion-design、video-shotcraft、pinepaper-studio、night-fiction-factory、literary-incident-response、tju-academic-office-generator |
| 第三方 Skills（宽松许可，完整源码+声明） | 5+2 | `skills/local/` + `THIRD-PARTY-NOTICE.md` | Alvarmethod 5 件（MIT）；mmc-helper（MIT，git 克隆件）；video-shotcraft（Apache-2.0，git 克隆件，**媒体资产未收录**） |
| License 不明（仅 manifest） | 1 | `skills/manifests/streamlit.md` | developing-with-streamlit：出处无法核实、上游无 License 文件 → 不公开源码 |
| Slash 命令 | 9 | `skills/local/_commands/` | 引用的 Skill 均已归档 |
| MCP 安装配方 | 10 | `mcp/install-recipes/` | 每服务器：用途、安装命令、脱敏 JSON 模板 |
| MCP 脱敏总模板 | 1 | `mcp/local/config-mcp-servers.template.json` | 删除前全量 10 服务器快照；zread token → `${ZREAD_TOKEN}` |
| 项目级配置示例 | 1 | `mcp/local/project-pinepaper.example.json` | Firefly_Animation_Test 的 pinepaper 项目级绑定 |
| Profile 切换器 | 1 | `mcp/local/zcode_mcp_profile.ps1` | 上一轮治理工具（自研） |
| 插件处置记录 | — | `plugins/manifests/` | marketplace 插件重装方式 + builtin 插件停用开关说明 |
| 审计数据 | — | `audit/` | REMOVE_SET、ORIGINAL_PATH_MAP、探针脚本与健康检查结果 |

## Secret 处理记录

- `cli/config.json` 原件**从未入库**；模板从零手写。
- zread `Authorization: Bearer …` → `Bearer ${ZREAD_TOKEN}`（并建议轮换旧 token）。
- video-shotcraft（上游 Apache-2.0 仓库自带的公开示例 token）→ `<REDACTED>`，9 处 token + 5 处 sec_uid。
- gitleaks 8.30.1 复扫 0 泄漏；2 条命中经人工核实为环境变量**名称**（`TJULLM_API_KEY_1`），指纹记录于 `.gitleaksignore`。
- 第二层扫描（关键词 + 香农熵）最终 0 命中（npm `sha512-` 完整性哈希属已知误报类，已排除）。

## 未收录说明

- video-shotcraft 的 `assets/audio`（BGM/SFX）与 `template/public` 纹理：随上游代码许可未能确认覆盖，未公开。
- `skill-sources/MathModelAgent`：上游克隆目录，仅记录原路径与体积，未公开源码。
- `~/.zcode/memory/mcp-memory.jsonl`（memory MCP 的私有数据文件）：**私有，未上传**；本地保留未删。
