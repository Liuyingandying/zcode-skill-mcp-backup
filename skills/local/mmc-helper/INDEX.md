# 全库地图

> 一句话说明每个文件"是什么、什么时候读它"。

## 根

| 文件 | 是什么 | 何时读 |
|---|---|---|
| `SKILL.md` | 主入口：锚定条款、四阶段、角色表、边界铁律 | **每次激活时先读** |
| `INDEX.md` | 本文件，全库地图 | 找不到东西时 |
| `CHANGELOG.md` | 发布后的版本变更记录（开发期历史另存，不在此列） | 升级后 |
| `CONTRIBUTING.md` | 贡献指南：文档分层约定、提交信息格式、不建议的改动 | 想改这个仓库时 |
| `README.md` | 对外说明（英文，仓库默认首页） | 首次接触 |
| `README.zh-CN.md` | 对外说明（中文） | 中文访问者 |

## `protocols/` — 协议层（**怎么做**）

| 文件 | 是什么 |
|---|---|
| `anchoring.md` | **强锚定**：skill 激活后持续生效，抗上下文压缩 |
| `startup_verify.md` | **启动自检**：新会话先校验状态与文件，差异为 0 才开工 |
| `handoff_protocol.md` | **交接与留痕**：三层留痕、交接文档限长、会话档 |
| `audit_protocol.md` | **审核**：隔离方式、触发点、报告结构、辩论留痕 |
| `batch_feedback_protocol.md` | **批量意见处理**：复述分类 → 影响面 → 顺序 → 执行；规则类意见全篇扫描 |
| `quality_control_protocol.md` | **三查两证**：文献与资料的真实性核验 |

## `agents/` — 角色卡（**谁来做、边界在哪**）

| 文件 | 角色 |
|---|---|
| `startup_agent.md` | 立项与预准备 |
| `modeler_agent.md` | 建模手 |
| `coder_agent.md` | 编程手 |
| `writer_agent.md` | **论文手**（含动笔前三闸门、五条机制、成稿复读） |
| `auditor_agent.md` | **审核手**（三张清单、交叉审查链、文档可读性验收） |
| `wrapup_agent.md` | 收尾 |
| `README.md` | **角色 × 协议矩阵** |

## `references/` — 参考层（**依据与知识**）

| 文件 | 是什么 |
|---|---|
| **`style_patterns.md`** | **写作范式库**：六条底层规律 + 句式用词 + 人称 + 图表写法 |
| **`known_pitfalls.md`** | **已知坑清单**（18 条，含如何检出） |
| `method_recommendation_matrix.md` | 方法谱系 + 问题特征 → 推荐矩阵 |
| `paper_structure_reference.md` | 优秀论文结构 + 高分要点 + 扣分点 |
| `format_presets.md` | 格式预设与排版自检 |
| `competition_profiles.md` | 竞赛 Profile 参数 |
| `state_schema.md` | `state.json` 权威状态 schema |
| `user_profile_schema.md` | 用户画像字段（跨比赛累积） |
| `ai_statement_templates.md` | AI 声明措辞原则与易错点（成文模板见 `templates/ai_statement_template.md`） |
| `growth_report_protocol.md` | 赛后成长报告 |
| `latex_bib_guidelines.md` | LaTeX / 引用库管理 |
| `lit_search_protocol.md` | 高精度检索 |
| `reading_io.md` | 读取与多模态约定 |
| **`tool_and_env_guide.md`** | **工具与环境适配**：技术栈盘点、能力缺失时的降级路径 |

## `templates/` — 模板层（**直接套用**）

| 文件 | 用途 |
|---|---|
| **`writing_contract_template.md`** | **写作契约**（增量台账） |
| **`latex_workflow.md`** | **LaTeX 工作流**：分章预览、一键编译、五项指标卡 |
| **`model_spec_template.md`** | **模型规格书**（固定骨架，可读性优先） |
| `session_archive_template.md` | 会话档 |
| `material_registry_template.md` | 素材登记表 |
| `audit_report_template.md` | 审核意见报告 |
| **`paper_writing_guide.md`** | **论文写作导引（主件）**：§〇 写作前准备 + 每章流程 + 结构 / 图表 / 返工控制 |
| `paper_format_rules.md` / `paper_skeleton_template.tex` | 格式规则与骨架 |
| `abstract_template.md` / `problem_analysis_template.md` / `result_summary_template.md` | 各阶段模板 |
| `ai_statement_template.md` / `growth_report_template.md` / `submission_checklist_template.md` | 收尾模板 |
| `state_init.json` | `state.json` 初始模板 |

## `examples/` — 示例

分阶段使用示例与算法样例。

## `paper-library/` — 获奖论文吸收归档

`notes/2023`、`notes/2024`（逐年逐篇提炼）+ `deep-reads/`（同题深读）+ `README.md`（索引）。
**读法**：立项时读一次建立印象；**正文动笔前再读一次**（第二次不可省）。
