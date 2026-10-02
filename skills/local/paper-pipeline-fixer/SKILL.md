---
name: paper-pipeline-fixer
description: 数学建模论文机械化生产管线。当用户要求"生成论文、组装 LaTeX、编译论文、检查论文引用图片表格、修论文编译错误、论文数值一致性检查"时使用。以 RESULTS_REPORT.md 为唯一数值来源：装配模板与正文（规避 run_001 的四类装配陷阱）、跑六项质量门（图片存在/数值溯源/表格换行/占位符/模板残留/路径泄露）、自动 xelatex 两遍编译并解析日志。生成内容由 Agent 撰写，机械装配与门禁由本管线负责。
---

# Paper Pipeline Fixer —— 论文机械化管线

## 硬性规则（全部源自 run_001 实证失败）

1. **RESULTS_REPORT.md 是唯一数值来源**：正文中每个小数必须在结果文件中找到（直接出现、×100、÷100 三种口径之一），否则视为编造。
2. **禁止 heredoc 生成 .tex**：Git Bash heredoc 会衰减 `\\`。正文一律经文件写入工具或脚本文件落盘。
3. **模板不可信**：装配前必须过 `repair` 规则（见下），不得直接使用捆绑模板原文件。

## 用法

```bash
python ~/.zcode/skills/paper-pipeline-fixer/scripts/build_paper.py <subcommand> ...
assemble --template <模板.tex> --body <正文body.tex> --out main.tex   # 前导提取+修复+拼装
check    --paper main.tex --results-dir DIR --figures-dir DIR        # 六项质量门
compile  --paper main.tex [--engine xelatex]                          # 两遍编译+日志解析
```

推荐顺序：Agent 写 body.tex（数值全部来自 RESULTS_REPORT.md）→ assemble → check（有 FAIL 回去改）→ compile → 6verity 交接。

## assemble 的 repair 规则（run_001 四连错固化为代码）

- 提取模板前导：取**第一个非注释行首的** `\begin{document}` 之前的部分（规避注释里的同名 token 切错位）
- 丢弃模板自带正文与示例摘要（模板作者的示例数据会污染论文）
- 无 graphicx 则补；无 `\graphicspath` 则按 figures-dir 补
- body 中 tabular 行尾单 `\` 自动补成 `\\`
- `\input{...}/\include{...}` 目标文件不存在时警告列出（正文引用一律视为 FAIL）

## check 六项质量门

1. 图片存在：`\includegraphics` 的每个文件在 figures-dir 可找到
2. **数值溯源**：正文小数 ∈ 结果文件文本（直接/×100/÷100）
3. 表格换行：tabular 环境内行尾单反斜杠 = FAIL
4. 占位符：TODO/FIXME/XXX/占位/待补/???
5. 模板残留：多余 `\begin{document}`、指向缺失文件的 `\input`、`X:\` 与 `/c/Users` 路径泄露
6. 编译前快检：`\end{document}` 恰好一个

输出结构化 JSON 报告 + 非零退出码（有 FAIL 时），供上层工作流门禁。
