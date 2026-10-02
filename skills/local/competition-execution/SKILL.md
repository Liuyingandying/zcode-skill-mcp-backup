---
name: competition-execution
description: Firefly Competition Execution——从"发现比赛"到"提交作品"的执行助手。当用户提到"参赛、准备比赛、比赛策略、参赛计划、提交检查、tracking 里的比赛"，或运行 /prepare-competition /competition-status /submit-check 时使用。基于 Project_Assets 项目资产与 competition_profile.yaml 画像做匹配；比赛信息必须经 research-knowledge MCP 核实，禁止凭空生成；文档生产必须调用 academic-office MCP。
---

# Firefly Competition Execution Agent v1

把 Competition Radar（发现端）的产出推进到"报名 → 准备 → 提交"（执行端）。
复用现有系统，不新建 MCP：**Research Knowledge MCP**（核实外部信息）、
**Academic Office MCP**（文档生产）、**Memory MCP**（决策留痕）、**competition-radar skill**（画像与简报）。

## 数据文件（单一事实源）

| 文件 | 作用 |
|---|---|
| `D:\glm生成计划\Firefly_Workflow\Project_Assets\*.yaml` | 三个参赛项目的资产描述（技术标签/可交付物/demo 状态/成熟度/缺口） |
| `C:\Users\FAJ\.zcode\skills\competition-radar\competition_profile.yaml` | 用户画像（背景/兴趣类别/偏好/排除项） |
| `D:\glm生成计划\Firefly_Workflow\Competition_Radar\TRACKING.yaml` | 追踪中的比赛（雷达写入，执行端更新状态） |
| `D:\glm生成计划\Firefly_Workflow\Competition_Radar\OPPORTUNITY_POOL.md` | 全球机会池（雷达 v2 维护，按 ①可报名/②即将截止/③远期高价值 组织） |
| `D:\glm生成计划\Firefly_Workflow\Competition_Radar\plans\` | 每场比赛的参赛计划（MD + docx） |

## 执行工作流（输入：比赛名称）

1. **获取比赛信息（必须走 MCP）**
   - 先查本地：`Competition_Radar\YYYY-MM-DD.md` 历史简报与 `TRACKING.yaml`；
   - 再联网核实：research-knowledge `web_search` 找官方入口 → **`fetch_page` 打开官网/官方规则**，
     提取：主办方、截止日期、参赛对象、赛道、提交物、费用；
   - 三级证据：官方规则/官网页 > 多个独立可靠来源交叉 > 聚合站快照（必须标"待复核"）。
   - **找不到可靠来源 → 如实回答"无法核实该比赛"，禁止输出任何臆造细节。**

2. **读取并匹配项目资产**
   - 逐个读取 Project_Assets YAML，按两层匹配：`technology_tags ∩ 比赛赛道关键词`（技术可行）
     与 `competition_tags ∩ 比赛主题`（方向对口）；
   - 命中后检查 `maturity.score` 与 `missing_items`：缺口直接转化为计划任务；
   - 输出匹配表：项目 × 贡献方式（主作品/组件复用/文档支持）× 复用成本。

3. **输出参赛策略**
   固定四段：定位（用哪个项目打哪条赛道、一句话卖点）｜复用映射（资产→提交物）｜
   差异化（创新点对比基线）｜风险（截止、资格、成本、缺口）。

4. **生成任务计划**
   - 以**官网核实的日期**为锚点倒排阶段：报名 → 素材 → 开发 → 打磨 → 提交 → 缓冲（≥3 天）；
   - 写入 `Competition_Radar\plans\<比赛短名>-<年份>-参赛计划.md`；
   - 计划中的每个任务标注：产出物、负责人（我/队友/导师）、所需资产。

5. **文档生产（必须走 MCP）**
   - 申报书/计划书/技术报告 → **必须调用 academic-office `generate_academic_docx`**，
     禁止手写 python-docx 或只给 Markdown 糊弄；
   - 生成后检查返回的 `details.format_audit`，六项门禁未过不得交付；
   - 任意第三方 docx 交付前跑 `format_audit.py <docx>`。

6. **状态回写**
   - 更新 `TRACKING.yaml`：status ∈ discovered → tracking → preparing → submitted → done/dropped；
   - 记忆留痕：用 Memory MCP 为比赛建实体（截止日期、策略、计划文件路径、关键决策）。

## TJULLM Tool Calling 规范（模型无关，TJULLM 重点优化）

**必须调用 MCP 的步骤（硬性）：**

| 步骤 | 必调工具 | 禁止的替代做法 |
|---|---|---|
| 比赛信息核实 | `mcp__research-knowledge__web_search` → `fetch_page` | 凭训练记忆写截止日期；只看聚合站快照 |
| 参赛文档生成 | `mcp__academic-office__generate_academic_docx` | python-docx 直写（曾导致格式全丢的事故） |
| 交付前检查 | `format_audit.py`（Bash） | 跳过检查直接交付 |
| 决策留痕 | `mcp__memory__create_entities / add_observations` | 只在对话里说，会话结束即丢 |

**TJULLM 调用优化：**
- 信息收集阶段把相互独立的 web_search **并行批量**发起（一次 2~4 组关键词）；
- fetch_page 前**先 web_search 拿准确 URL**，避免对 JS 重页（devpost/facebook）浪费调用，优先官方规则 PDF、GitHub README、高校教务通知这类静态页；
- `generate_academic_docx` 的 content 用**完整 Markdown 一次传入**（含参考文献节），不要分多次生成再拼接；
- 引用事实时在回答中标注来源 URL 与核实日期；无法核实的字段一律写"未知（原因）"。

## Tracking 状态机

```
discovered（雷达发现）→ tracking（确认值得打）→ preparing（有计划在推进）
→ submitted（已提交）→ done / dropped
```

`TRACKING.yaml` 每条目字段：name / stars / status / deadline / deadline_source /
official_url / match_projects / discovered / next_action / plan_file（进入 preparing 后必填）。

## 与现有系统的关系

- `competition-radar` skill：发现端（每天 9:00 自动化），五星机会写入 TRACKING.yaml 后进入本 skill 管辖；
- `/prepare-competition <比赛>`：一键执行本工作流第 1~6 步；
- `/competition-status`：全部追踪项状态总览；
- `/submit-check <比赛>`：提交前门禁（截止复核 + 交付物清单 + format_audit）→ GO/NO-GO。
