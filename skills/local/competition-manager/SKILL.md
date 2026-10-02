---
name: competition-manager
version: 0.1.0
description: 数学建模比赛任务管理器。当用户提到"管理比赛、多个比赛、比赛排序、是否值得参加、参赛决策、评估比赛、比赛项目目录、比赛进度跟踪、执行计划"，或要求对若干比赛"排个优先级/制定参赛计划"时使用。纯本地运行（无外部 API），负责 发现之后的 决策评估 → 建项目 → 排计划 → 跟进度 → 衔接建模 workflow。比赛信息发现/核实请用 competition-radar，提交检查请用 competition-execution。
---

# Competition Manager —— 比赛任务管理器

管理多个数学建模比赛任务的完整生命周期：**录入 → 评估 → 建项目 → 排计划 → 跟进度 → 交接建模**。

## 硬性约束

1. **纯本地**：本 skill 不调用任何外部 API/网络请求。比赛信息由用户提供或经 competition-radar 核实后手工录入。
2. **只读其他 skill**：允许读取（如 `~/.zcode/skills/2analysis-modeling/SKILL.md`）以了解 workflow 接口，**绝不写入/修改任何其他 skill 目录**。
3. **数据与逻辑分离**：skill 目录只放逻辑与模板；所有用户数据（数据库、项目目录）写在当前工作区根目录。

## 数据契约（v1）

- 数据库：`<工作区>/competitions.json` —— 顶层对象 `{version, updated, profile, competitions[]}`，
  每条记录含必需字段：`competition_name, deadline, category, difficulty, topic, required_tools, status`
  及管理字段：`id, level, worth_score, decision, score_breakdown, project_dir`
- 项目目录：`<工作区>/competitions/<id>-<简称>/`，脚手架与"各阶段产物落点"见 `references/design.md`
- 项目状态：`<项目目录>/project.json` —— 状态机 + 历史记录

status 枚举：`discovered → evaluating → registered → modeling → coding → writing → review → submitted`，终态 `submitted / dropped / expired`

## 使用方式

一律先 `cd` 到工作区根目录（数据库所在处），再运行脚本：

```bash
python ~/.zcode/skills/competition-manager/scripts/manager.py <command> ...
```

| 意图 | 命令 |
|---|---|
| 录入比赛（自动建项目目录） | `add --name "XX赛" --deadline 2026-10-08 --category 数据分析 --difficulty 2 --topic "..." --tools python,pandas --level 省级` |
| 评估是否值得参加 | `evaluate` |
| 输出排序 + 执行计划 | `plan [--save]` |
| 更新进度 | `track --id C-001 --status modeling --note "Q1 已完成回归"` |
| 快速列表 / 总览 | `list` / `report` |

## 工作流程（Agent 按此执行）

1. **录入**：用户给出比赛信息 → `add`（缺失字段：difficulty 默认 3，level 未知则省略，category 必须确认）。
2. **评估**：`evaluate` 后，向用户口头解释分数构成（价值/时间可行性/难度匹配/工具就绪四项），**决策权在用户**，脚本只给建议。
3. **计划**：`plan` 输出排序与分阶段日期计划；有冲突（时间重叠、工具缺失）必须显式告知。
4. **开工**：用户确认参加后，`track --status modeling`，然后按顺序交接给数学建模 workflow：
   - 赛题分析/建模设计 → 读并遵循 `2analysis-modeling`（产物 → `30_models/`）
   - 编程实验 → `3coding-visual` / 数据三件套 `mathmodel-data-tools`（结果 → `50_results/`）
   - 流程图 → `4drawio`；论文 → `5writing`（配合 `60_paper/` 的 LaTeX 模板）；验收 → `6verity` 或 mmc-helper 审核手
5. **跟踪**：用户汇报进展或阶段性产出完成时，`track` 更新状态；每次 `report` 输出全局进度总览。

## 评分模型（无 API，纯启发式，详见 design.md）

`worth = 价值(0-30) + 时间可行性(0-30) + 难度匹配(0-20) + 工具就绪(0-20)`
决策阈值：≥75 强烈推荐 ｜ 55-74 推荐 ｜ 35-54 备选观察 ｜ <35 不建议 ｜ 已截止直接标记。
