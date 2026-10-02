---
name: paper-miner
description: 优秀论文结构化导入 skill（paper-miner）。当用户提到"导入论文、论文挖掘、paper mining、优秀论文入库、paper_dataset、结构化论文"时使用。对本地论文 PDF 执行 scan（清点/O奖过滤）→ extract（PyMuPDF 文本提取）→ mine（词典抽取模型/算法 + 结构解析）→ record（生成 paper_record.json 八字段）→ kb.py 注册进 knowledge_base/paper_dataset。客观字段（题型/模型/算法/引用）机器抽取；judgment 字段（innovation/strengths/weaknesses/review_hooks）由 LLM 辅助撰写并标注 authored_by，需人工抽查。
---

# paper-miner —— 优秀论文结构化导入

## 硬性约束

1. 只写 `knowledge_base/paper_dataset/`（meta/ + records/），**不修改** modeling workflow、modeling-reviewer、paper-pipeline-fixer 的任何文件。
2. **PDF+meta+record 三件套才算入库**；meta 必须经 `knowledge_base/kb.py add --layer paper_dataset` 注册（否则不可检索即不存在）。
3. 客观字段必须带证据（匹配行摘录/页码），judgment 字段必须标注 `authored_by`。
4. 文本量 <2000 字符的 PDF 判为扫描件，标记 `needs_ocr` 跳过（v0.1 不做 OCR）。
5. 不复制 PDF 原文进 KB（记录 `source_path` 即可；原文搬入属后续全量导入决策）。

## 管线

```
scan.py   --root <论文库根目录> --years 2023,2024,2025 [--out inventory.json]
extract.py --inventory inventory.json --ids id1,id2 [--cache-dir cache/]     # PyMuPDF
mine.py   --text cache/<id>.txt --inventory inventory.json [--out records/]  # 词典抽取+结构解析
# judgment 字段: agent 读 raw_abstract/sections 后填写 judgments.json, 再 merge 进 record
# 入库: kb.py add --layer paper_dataset --file meta/<id>.json
```

## paper_record 八字段契约

`problem_type`（官方题型 by 题号映射 + KB 建模分类）、`models_used`（模型词典命中+证据行）、`algorithms`（算法词典命中）、`innovation` / `strengths` / `weaknesses`（LLM 辅助判断）、`review_hooks`（可反哺 modeling-reviewer 的陷阱/校验清单）、`references`（文献区计数与样式）。

## 题号→官方题型映射（MCM/ICM 稳定约定）

A=连续(Continuous) B=离散(Discrete) C=数据洞察(Data Insights) D=运筹/网络(Operations Research/Network) E=可持续(Sustainability) F=政策(Policy)
