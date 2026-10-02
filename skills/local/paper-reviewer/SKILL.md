---
name: paper-reviewer
description: 论文语义质量审查（paper-reviewer v0.1）。当用户提到"审查论文质量、论文体检、结构完整性检查、摘要检查、学术文本检查、提交前评审"时使用。六模块：M1 结构完整性（对照 O 奖骨架）/ M2 数值溯源（委托 paper-pipeline-fixer）/ M3 图表规范 / M4 学术文本质量门（连接词密度、拔高词、引文、参数一致性、术语统一）/ M5 摘要三段式 / M6 领域失败案例对照（KB 简报）。原子扣分制评分，全部检查输出证据位置。只报告不修复。
---

# paper-reviewer v0.1

分工：机械门=paper-pipeline-fixer（M2 委托其 check 子命令）；建模方案=modeling-reviewer（上游 RISK_REPORT 未闭合项进 M6）；提交验收=6verity（下游）。本 skill = 论文文档语义质量层。

```bash
python scripts/paper_reviewer.py --paper-dir <work/60_paper> \
  --results-dir <work/50_results> --problem-type 机理建模 \
  --competition cumcm [--out-dir paper_dir/_review]
```

输出：paper_review_report.json / PAPER_REVIEW.md / review_trace.json；exit 0=提交就绪(≥90) 1=需修改(75-89) 2=返工(60-74) 3=退回(<60)。
评分：100−Σ扣分（原子 1/2/3 档，评分前冻结检查表，不重复扣分）。KB 接口：M6 调 kb_review_brief.py 按题型取 failure_cases/model_patterns 检查项池；新型失败模式写入 failure_cases/_mined_v04.json staging。
