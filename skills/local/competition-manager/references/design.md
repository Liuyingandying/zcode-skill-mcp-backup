# Competition Manager 设计文档（v0.1 · 最小可运行版）

日期：2026-09-24 ｜ 约束：纯本地无外部 API；不修改任何已有 skill；复用已装数学建模 skills 与 MCP 环境

## 1. 定位与边界

数学建模 Agent 工作流全链路：

```
比赛发现(radar) → 【决策评估 → 建项目 → 排计划 → 跟进度】(本 skill) → 建模workflow(2~6 pipeline/mmc-helper) → 文档整理 → 提交(execution)
                    └──────────────── competition-manager ───────────────┘
```

- 上游：competition-radar 负责发现与核实；本 skill 假定输入信息已可信。
- 下游：建模执行交给既有 pipeline skill（2analysis-modeling → 6verity）；本 skill 只负责把项目"摆好"并跟踪状态。
- 明确不做：外部 API 调用、报名自动化（Level 3 的 browser-use 事项）、论文内容生成。

## 2. 项目目录规范

每场比赛一个项目目录，编号即生命周期顺序：

```
<工作区>/
├── competitions.json                  # 比赛数据库（唯一事实源）
├── plans/                             # plan --save 的历史计划
└── competitions/
    └── C-001-<简称>/
        ├── project.json               # 项目元数据 + 状态机 + 历史
        ├── 00_admin/                  # 报名信息、官方规则、截止时间线
        ├── 10_problem/                # 题目原文、附件、题面解析
        ├── 20_data/raw|processed/     # 原始/清洗后数据（mathmodel-data-tools 三件套的 L1 中间层放 processed/）
        ├── 30_models/                 # 建模方案（2analysis-modeling 产物 ANALYSIS_MODELING_REPORT.md）
        ├── 40_exp/                    # 实验代码（3coding-visual / 4drawio 工作区）
        ├── 50_results/                # RESULTS_REPORT.md + figures/
        ├── 60_paper/                  # 论文源（5writing：main.tex/typst）与编译产物
        ├── 70_review/                 # 验收记录（6verity / mmc-helper 三查两证）
        └── archive/                   # 过程稿归档
```

### 与既有 skill 的产物落点映射（关键，因不修改上游 skill）

| 上游 skill | 期望产物 | 本规范落点 |
|---|---|---|
| 2analysis-modeling | ANALYSIS_MODELING_REPORT.md | 30_models/ |
| 3coding-visual | RESULTS_REPORT.md、figures/*.pdf | 50_results/ |
| 4drawio | DRAWIO_REPORT.md、流程图 PDF | 50_results/figures/ |
| 5writing | main.tex / typst 工程 | 60_paper/ |
| 6verity / mmc-helper 审核手 | 验收/审核记录 | 70_review/ |

> 运行上游 skill 时以项目目录为工作目录，产物按上表归位（skill 输出在项目根时由 Agent 移动归档）。

## 3. 数据库格式（competitions.json）

```json
{
  "version": 1,
  "updated": "2026-09-24",
  "profile": { "team_size": 3, "hours_per_week": 20, "skill_level": 3 },
  "competitions": [
    {
      "competition_name": "...",
      "deadline": "2026-10-08",
      "category": "数据分析",
      "difficulty": 2,
      "topic": "...",
      "required_tools": ["python", "pandas"],
      "status": "discovered",
      "id": "C-001",
      "level": "省级",
      "worth_score": 81,
      "decision": "强烈推荐",
      "score_breakdown": { "value": 18, "time": 30, "difficulty_fit": 13, "tools": 20 },
      "project_dir": "competitions/C-001-xxx"
    }
  ]
}
```

必需七字段即题目要求；`id/level/worth_score/decision/score_breakdown/project_dir` 为管理扩展。status 枚举：
`discovered → evaluating → registered → modeling → coding → writing → review → submitted`，旁路 `dropped`；截止即 `expired`。

## 4. 评估模型（worth，0-100，纯启发式）

| 维度 | 满分 | 规则 |
|---|---|---|
| 比赛价值 | 30 | level 关键词映射：国家级A/国赛 30 · 美赛 28 · 国际 26 · 国家级B 24 · 省级 18 · 市级 14 · 校级 10 · 未知 15 |
| 时间可行性 | 30 | 所需天数 = 4 + 2×difficulty；ratio = 剩余天数/所需天数，ratio≥1.5 记满，线性降到 0.5 处为 0；已截止 0 |
| 难度匹配 | 20 | 20 − 7×\|difficulty − profile.skill_level\|，下限 0 |
| 工具就绪 | 20 | 按 `TOOL_AVAILABILITY`（源自 2026-09-24 环境审计）逐个核对：有 1 · 无 0 · 未知 0.5，取均值×20 |

决策阈值：≥75 强烈推荐 ｜ 55-74 推荐 ｜ 35-54 备选观察 ｜ <35 不建议 ｜ 截止 → expired。
模型刻意简单、可解释、零依赖——评估是"给用户看的参考"，**最终参赛决策永远由用户做出**。

## 5. 执行计划生成（plan）

- 排序：accepted（未截止且 decision 非不建议）按 worth 降序。
- 每项输出：建议启动日 = deadline − 所需天数 − 1 天缓冲（早于今天则标注"需立即启动或放弃"）；
  五阶段日期切片：题析 15% / 建模 25% / 编程 30% / 论文 25% / 验收 5%。
- 冲突检测：多个比赛的 [启动日, 截止日] 区间重叠 → 显式警告；required_tools 中不可用项 → 列为风险。

## 6. 与 ZCode 能力的集成点（本期不实现，预留接口）

- 截止提醒：用户要求时用 ZCode 原生 CronCreate 建"每 09:00 检查 competitions.json 即将截止项"的定时任务（不属本 skill 代码）。
- 多 Agent 编排：`plan` 产出的阶段切片即 CreateWorkflow 的任务序列蓝本。
- 自动报名（Level 3）：browser-use 填表，本 skill 的 `00_admin/` 存放报名凭据模板与表单字段。

## 7. 最小可运行版本范围（本期实现）

`scripts/manager.py`（纯 Python 标准库，~350 行）：add / evaluate / plan / track / list / report 六个子命令 + 项目脚手架生成 + JSON 数据契约读写。已知取舍：不支持并发写、无单元测试（模拟运行作验收）、评分常数硬编码在文件头便于赛前调整。
