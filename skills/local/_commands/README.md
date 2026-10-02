# Firefly Agent Commands（用户级）

> 位置：`C:\Users\FAJ\.zcode\commands\`（ZCode 用户级命令目录，对所有工作区生效）
> 创建：2026-09-19 ｜ 设计方案：`D:\glm生成计划\Firefly_Workflow\Firefly_Agent_Commands_Hooks设计方案.md`

## 命令列表

| 命令 | 文件 | 参数 | 用途 |
|---|---|---|---|
| `/status` | `status.md` | 可选：重点关注对象 | 扫描当前工作区，生成六段式项目状态报告（项目名称/当前阶段/最近完成/存在问题/下一步/风险 + 重点关注 Firefly AI Pet、THz-ISAC、FPGA 项目、Research 目录） |
| `/report` | `report.md` | 主题与要求 | 生成正式学术文档：整理内容 → Markdown → 自动挂载 `tju-academic-office-generator` 管线 → 真实 docx（可加 PDF）。适用于实验/调研/课程报告、项目总结 |
| `/meeting` | `meeting.md` | 组会主题（默认 THz-ISAC） | 生成组会五件套：汇报结构、PPT 大纲、核心公式/技术点、老师可能提问、回答准备 |
| `/competition` | `competition.md` | 可选：方向过滤 | 联赛检索+匹配分析，只输出 ≥3 星高价值机会（名称/截止/要求/匹配项目/准备成本/推荐程度） |
| `/release` | `release.md` | 项目名称 | 生成 README 六段草稿到 `<项目>/README.release-draft.md`，不覆盖已有 README |

## 使用方法

- 新开一个 ZCode 会话（命令在会话启动时加载），在输入框输入 `/` 即可在 Commands 分组看到五个命令。
- 参数直接跟在命令后：`/meeting THz-ISAC 成像链路进展`、`/report 高频超声成像实验报告 素材在 D:\data\lab3`。
- 不带参数时各命令有内置默认行为（见上表）。

## 修改与新增

- 命令名 = 文件名（小写字母/数字/`_-:`，≤64 字符，不得有空格或点）。
- frontmatter 只用单行键：`description`、`argument-hint`、`allowed-tools`、`model`、`skills`、`disable-noninteractive`；`description` 或正文必须非空。
- 正文支持 `$ARGUMENTS`（全部参数）与 `$1`/`$2`（位置参数）；**不要**使用 `` !`命令` `` 动态 shell（会被拒绝加载）。
- 同名命令"先发现者胜"：用户级 `~/.zcode/commands` 优先于 `~/.agents/commands`、工作区与插件；若某个命令在 `/` 菜单消失，先检查是否被同名高优先级文件或内置命令（如 `compress`）遮蔽，改个文件名即可。

## 注意事项

- `/status`、`/release` 只反映**当前工作区**能扫描到的内容；THz-ISAC、FPGA、TIA 等项目若不在当前工作区，报告会如实标注"未发现"。
- `/competition` 依赖联网检索，注意核对官网截止日期；每天 9:00 已有"比赛机会雷达"定时自动推送，本命令用于按需深挖。
- `/report` 产出真实文件；生成的 Markdown 草稿与 docx 默认放在当前工作区 `Reports/` 目录。
