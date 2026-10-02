# templates/ — 各阶段模板

> **留痕写作风格（所有记录型模板统一遵循）**：
> 留痕留档是**给人读的**，不是给机器填的表。文体要求：
> 1. **正文用流畅叙述**：向协作者讲清楚一件事——先结论、再推理、再关键细节；能独立理解，不必回看其它文件。
> 2. **只有真正是表格的数据才用表格**：参数、结果指标、候选比较、达标判据核对这类才用 Markdown 表；**思考/理由/解释一律用段落**。
> 3. **结构用标题组织**，不堆 `[ ]` 占位；填空用自然句子。
> 4. **文末放"自检/必填"清单**：把"必须完整"的纪律（如参数已定义、引用已验证）集中成文末清单，而不是散落成字段行。
> 5. **克制"官方腔"**：避免"兹/鉴于/综上所述"这类套话，用清楚、直接、易于理解的语言。

## 模板一览
| 文件 | 用途 | 阶段 | 文体 |
| --- | --- | --- | --- |
| `problem_analysis_template.md` | 题目剖析（理解/逐问拆解/数据/候选/反驳/确认） | Phase 1 | 叙述为主 |
| `model_spec_template.md` | 模型规格书（假设/数学形式/参数/算法/预期输出/达标判据） | Phase 2·建模手 | 叙述 + 参数表 |
| `result_summary_template.md` | 结果摘要（复现/结果/达标核对/解释/异常回环） | Phase 2·编程手 | 叙述 + 结果表 |
| **`paper_writing_guide.md`** | **论文写作思路导引（主件）**：每部分怎么写、从哪取素材、受阻怎么办、写作节奏；§〇 写作前准备（格式先行） | Phase 2·论文手 | 导引 |
| **`paper_format_rules.md`** | **格式与版式规则（写作前必读·准备模板）**：结构对齐模板、摘要页版式、三线表单对行、题注一行主标题、长公式分行、小标题纪律、去花哨、防溢出；§7 逐节自检 + §8 收尾渲染终检 | Phase 2·论文手（每个小问开写前）+ Phase 3 | 规则 |
| `paper_skeleton_template.tex` | **格式参考**：**默认对齐国赛官方模板层级**的 LaTeX 骨架（写作前先定层级；含安全默认：hidelinks/三线表示例/防溢出注）；思路见写作导引 | Phase 2·论文手 | 排版 |
| `abstract_template.md` | 摘要（中/英四段式 + 自检） | Phase 3 | 叙述 |
| `submission_checklist_template.md` | 提交前 Checklist | Phase 3 | 清单 |
| `ai_statement_template.md` | AI 使用声明（紧凑/宽泛 + 按条款） | Phase 3 | 叙述 |
| `growth_report_template.md` | 赛后成长报告（每次必写 + 回写 user_profile） | Phase 3 | 叙述 |
| **`writing_contract_template.md`** | **写作契约**（增量台账）：禁用/必用、人称、章节职责、表格与引用规范；用户每提一条要求即入表并全篇执行 | Phase 2·论文手 | 台账 |
| **`latex_workflow.md`** | **LaTeX 工作流**：工程组织、单章预览、引用编号保全、一键编译、**五项编译指标卡**；其它排版工具的通用要求见 `references/tool_and_env_guide.md` §3.2–§3.3 | Phase 2·论文手（选用 LaTeX 时） | 导引 |
| `session_archive_template.md` | 会话档：一次会话谈了什么、结论、改了哪些文件 | 全程 | 叙述 |
| `material_registry_template.md` | 素材登记表：文件 → 用途 → 正文引用位置 → 生成程序 → 数据来源与粒度 | Phase 2·编程手 | 表格 |
| `audit_report_template.md` | 审核意见报告（含「历史缺陷重犯检查」与应答栏） | Phase 2·审核手 | 叙述 + 表 |
| `state_init.json` | `_mmc_internal/state.json` 初始化骨架 | 运行时 | 数据 |

## 模板与交接的关系
- 建模手→编程手靠 `model_spec_template`（交前自检：良定/可解/参数/预期输出/达标判据）。
- 编程手→论文手靠 `result_summary_template`（复现/可解释/图定稿）。
- 论文手→收尾靠论文骨架 + 摘要 + checklist；收尾靠 `submission_checklist` + `ai_statement` + `growth_report`。
- **写作契约**在论文手动笔前建立，随项目增量维护；**素材登记表**在编程手每产出素材时即时登记；
  **审核报告**在每次验收（T1/T2/T3）产出；**会话档**在每次会话结束时写。
