# 《academic-office-generator v2.0 升级方案》

> 日期：2026-09-19 ｜ 目标：Word 生成达到中国高校本科论文/课程报告/科研调研报告正式排版规范
> 约束：不改 MCP Server（server.py 零改动）、MCP 接口四参数保持兼容、优先改 Skill 内部脚本、不破坏已有功能

## 1. 当前格式实现方式（v1.x 现状）

| 格式项 | v1 实现方式 | 保障层级 |
|---|---|---|
| 中文字体（宋体/黑体） | postprocess 三层强制（docDefaults/样式/run 级 eastAsia） | ✅ 程序化 |
| 西文字体 Times New Roman | 同上（ascii/hAnsi 槽位） | ✅ 程序化 |
| 标题编号 1 / 1.1 | 文字前缀（幂等），默认 2 级，`--number-levels 3` 可开 3 级 | ✅ 程序化 |
| 自动目录 | 标准 TOC 域 + updateFields | ✅ 程序化 |
| 图表题注 | SEQ 域"图 N/表 N" | ✅ 程序化 |
| 表格宽度/字号 | polish_tables 实测定宽 + 10.5pt | ✅ 程序化 |
| 字号/加粗/标题颜色 | 仅依赖 reference.docx 样式继承，postprocess 不强制 | ⚠️ 隐式 |
| 页面设置（A4/页边距） | 完全依赖 reference.docx | ⚠️ 隐式 |
| 页眉/页脚/页码 | 无 | ❌ 缺失 |
| 正文首行缩进 2 字符/1.5 倍行距/段后 6pt | 无强制 | ❌ 缺失 |
| 三级标题编号 | 默认关闭 | ❌ 缺失 |
| 题注五号宋体 | polish 只管表格内文字，题注字号未强制 | ❌ 缺失 |
| 参考文献 GB/T 7714 排版 | 无（原样正文格式） | ❌ 缺失 |
| 文档类型（论文/课程报告/竞赛申报书） | 无区分 | ❌ 缺失 |

## 2. 当前不足

1. pandoc reference.docx 的 Heading 样式带蓝色/斜体等 Word 默认外观，v1 未强制黑色/加粗/字号，视觉上"不像中文论文"。
2. 正文段落（Body Text / First Paragraph）无首行缩进与行距控制，段间距默认 0，不符合"首行缩进 2 字符、1.5 倍行距、段后 6pt"。
3. 无页眉"天津大学本科课程/科研报告"、无页脚页码域。
4. TOC 占位与"目 录"标题字号字体未控制；TOC 条目字体取决于 Normal 继承，无小四宋体保证。
5. 题注未强制五号宋体居中（v1 加粗但不控字号）；图片无版心宽度适配，大图会溢出页面。
6. 参考文献与正文同格式，无五号宋体、无悬挂缩进、无 [n] 编号保证。
7. 只有一种隐式样式，无法区分科研论文/课程报告/竞赛申报书。

## 3. 修改与新增文件

**修改（Skill 内部，主体工作）：**
- `scripts/postprocess_docx.py` → v2.0：新增页面设置、页眉页脚（PAGE 域）、标题样式强制（黑体/字号/加粗/黑色/间距）、正文段落格式（缩进/行距/段后）、题注五号宋体、参考文献 GB/T 7714 重排、图片版心适配；`--style` 参数；三级编号默认开启
- `scripts/verify_output.py` → v2.0：新增页面/页眉页脚/标题样式/正文样式/参考文献 5 组检查
- `SKILL.md`、`references/word-recipe.md` → 文档同步 v2.0

**新增（Skill 内部）：**
- `scripts/style_config.py` —— STYLE_CONFIG 统一管理三种文档类型的字体/字号/页面/标题/段落配置（消灭硬编码）
- `scripts/backup_v1/` —— v1 脚本备份（已就位）

**修改（MCP 侧，最小化）：**
- `E:\Firefly_AI_MCP\academic_office_mcp\tools.py`：TEMPLATE_MAP 增加 `academic_paper` / `course_report` / `competition_report` 三个键（与 `tju` 同指 reference.docx），并把 style 名透传给 postprocess `--style`。**server.py 与接口签名零改动**——style 通过既有 `template` 参数选择，旧调用 `template="tju"` 行为不变（自动落在新默认 academic_paper 上）。

## 4. 风险

1. **样式名依赖 pandoc**：正文格式只挂在 Body Text / First Paragraph 上，Compact（表格/紧凑列表用）显式排除并归零缩进，防止表格与列表被误缩进。
2. **幂等性**：页面/页眉/页脚/参考文献均先探测再写入，重复运行不叠加。
3. **verify 收紧导致 v1 旧文档自检失败**：属预期行为（v2 门禁按 v2 标准检查），文档中注明。
4. **TOC 1/2/3 样式可能不存在**（Word 打开域更新时才创建）：用 try/except 兜底，缺失时靠 docDefaults+Normal 保证宋体小四。
5. **页眉出现在目录页**：简化处理（正式论文封面页免页眉需 section 分节，列为后续）。
6. 首行缩进用 `firstLineChars=200`（字符级、随字号缩放）+ 24pt 兜底双写，Word/WPS 均生效。

## 5. 测试方案

1. **v2 功能测试**：生成《THz-ISAC技术调研报告》，内容覆盖摘要/一级/1.1/1.1.1 三级标题/图片占位（PIL 生成占位图）/Markdown 表格/GB/T 7714 参考文献；断言 7 项——可打开、正文宋体小四、西文 Times New Roman、标题黑体三/四/小四加粗、TOC 存在、页眉页脚存在、verify_output.py 全项通过。
2. **MCP 回归**：重跑 `test_mcp_e2e.py`（17 项），证明 `template="tju"` 旧路径不回归。
3. **style 切换测试**：`template="course_report"` 直接调用 tools.py，断言页眉文案切换。
4. **视觉审查**：Word COM 转 PDF → pymupdf 渲染 PNG → 交 judge 智能体按用户验收标准评审。
