---
name: tju-academic-office-generator
description: 科研/课程/竞赛文档生产助手：把实验记录、图片、数据表格、Markdown 笔记、PDF 论文生成为正式的 Word(docx)、PDF、PPT 文件。只要用户提到"生成/写 实验报告、课程答辩 PPT、论文整理、大作业报告、结题报告、竞赛申报书、开题汇报"，或要求"转成 docx/pdf/pptx/Word/PPT/幻灯片/演示文稿"，或给出实验数据要求产出可提交的文档，都必须使用本 Skill——产出真实文件并自检，绝不只回复 Markdown 文字。
---

# TJU Academic Office Generator (v2.0)

把用户的实验记录、图片、数据表格、笔记生成**真实可提交的 .docx / .pdf / .pptx 文件**，格式符合中国高校学术规范（A4 页面与标准页边距、页眉报告头、页脚页码、标题黑体、正文宋体、首行缩进 2 字符、自动编号、自动目录、图表题注、GB/T 7714 参考文献、WPS 兼容）。

**v2.0**：格式数值统一由 `scripts/style_config.py` 管理（`academic_paper` 科研论文 / `course_report` 课程报告 / `competition_report` 竞赛申报书 三种文档类型），postprocess 负责页面设置、页眉页脚、标题样式、正文段落格式、图片版心适配与参考文献排版；`postprocess_docx.py --style` 与 `verify_output.py --style` 选择文档类型。

三条铁律：

1. **必须产出文件**。用户拿到手的是 `xxx.docx`、`xxx.pdf`、`xxx.pptx`，不是一段 Markdown。回答里给出文件的绝对路径。
2. **不手写 Office 解析器**。文档构建用已配置的 MCP（pandoc / word-document-server / ppt-server），格式补齐与自检用本 Skill 自带脚本（`scripts/`，纯 python-docx / python-pptx / pypdf / COM，均为成熟开源库）。
3. **交付前必须自检**。每次生成后运行 `scripts/verify_output.py`，把检查结果如实报告给用户；检查失败就修复后再交付。

## 第一步：判断输出类型

| 用户意图关键词 | 输出 | 主管线 |
|---|---|---|
| 实验报告、大作业报告、结题/验收报告、论文整理、技术文档、申报书 | `xxx.docx` + `xxx.pdf` | pandoc → docx → 后处理 → Word COM 转 PDF |
| 课程答辩、开题/组会汇报、竞赛路演、PPT、幻灯片、演示 | `xxx.pptx` | ppt-server 结构化构建（或 pandoc 快速稿）→ 字体修复 → 自检 |
| 只说"整理成文档/报告"，无明确格式 | 默认 `docx` + `pdf` | 同报告管线 |
| 要求"docx 模板填空"（学校/公司发来的模板） | 按模板的 `docx`(+pdf) | 见 references/mcp-servers.md 的模板填空方案 |

无法判断时（如"帮我处理这个实验数据"）先问一句要什么产出；能判断就直接做，不要反复确认。

## 工具路由

按优先级使用；**MCP 工具不可用时自动降级到 pandoc CLI / 本 Skill 脚本**，产物要求不变：

| 能力 | 首选 | 降级 |
|---|---|---|
| Markdown → docx（带样式） | `mcp__pandoc__convert-contents`（`output_format: docx`，`reference_doc` 指向本 Skill 的 `assets/reference.docx`） | `pandoc 输入.md -o 输出.docx --reference-doc=reference.docx` |
| docx 精细编辑（表格/图片/替换/脚注） | `mcp__word-document-server__*`（54 个工具，速查见 references/mcp-servers.md） | `scripts/` 里的 python-docx 逻辑 |
| PPT 构建（模板/图表/图片/版式） | `mcp__ppt-server__*`（37 个工具，`create_presentation_from_template` 可用本 Skill `assets/reference.pptx`） | `pandoc 笔记.md -o 输出.pptx --reference-doc=reference.pptx` |
| docx → pdf | `scripts/convert_pdf.py`（Word COM → WPS COM → soffice 自动降级，转换前自动刷新目录域） | `mcp__word-document-server__convert_to_pdf`（需要 MS Word） |
| 中文字体/编号/目录/题注/页面/页眉页脚/参考文献补齐 | `scripts/postprocess_docx.py`（**docx 必跑**，`--style` 选文档类型） | — |
| PPT 中文字体补齐 | `scripts/fix_pptx_fonts.py`（**pptx 必跑**） | — |
| 交付前自检 | `scripts/verify_output.py` | — |

`SKILL_DIR` 指本 Skill 目录：`C:\Users\FAJ\.agents\skills\tju-academic-office-generator`。

**为什么 docx 后处理不可省**：调研确认（详见 references/mcp-servers.md）这些开源 MCP 都不处理中文 eastAsia 字体（python-docx 只写 latin 字体，中文会回落默认字体），Word MCP 没有 TOC 工具、没有图表题注编号。这三个恰好是中文报告的硬规范，由 `postprocess_docx.py` 用标准 Word 域（TOC/SEQ）补齐，Word 和 WPS 都原生支持。

## 标准流程 A：实验报告 / 论文整理（docx + pdf）

1. **收集素材**：读用户的实验记录/笔记/数据表格（csv、xlsx、md、txt 均可），图片记下绝对路径。数据表格用 xlsx/csv 读取后整理成 Markdown 表格。**需要新画数据图时**（matplotlib/PIL）必须显式指定中文字体（如 matplotlib `plt.rcParams["font.sans-serif"]=["SimHei"]`，PIL 加载 `C:\Windows\Fonts\simhei.ttf`），否则图内中文是方块；图中的数值必须与正文表格一致。
2. **写 Markdown 中间稿**（放在输出目录，如 `报告名.md`）：
   - **题目放 YAML frontmatter**（pandoc 会用 Title 样式渲染，不参与编号）：文件开头写
     ```yaml
     ---
     title: 报告题目
     ---
     ```
   - 章节用 `# 章节名`、`## 小节名`（**不要手写编号**，后处理会加；写 `# 引言`、`# 实验方案`、`# 结果与分析`、`# 结论`、`# 参考文献`）
   - 图片用绝对路径：`![图注文字](E:/path/to/fig1.png)`——图注写在 `![ ]` 里，后处理会转成"图 N 图注"格式
   - 表格用 Markdown 表格，并在**表格正上方**加一行 `表：表注文字`，后处理会转成"表 N 表注"
   - 数据如实引用用户给的数值，不许编造；缺数据的地方明确留"待补充"
3. **转 docx**：
   ```
   pandoc 报告名.md -o 报告名.docx --reference-doc="<SKILL_DIR>/assets/reference.docx" --resource-path=<图片所在目录>
   ```
   或等价调用 `mcp__pandoc__convert-contents`。`assets/reference.docx` 已内置黑体/宋体/字号/行距学术样式。
4. **后处理**（必须）：
   ```
   python "<SKILL_DIR>/scripts/postprocess_docx.py" 报告名.docx
   ```
   默认执行：eastAsia 字体强制（标题黑体/正文宋体）+ 一二级标题自动编号 + 目录域（打开时自动更新）+ 图表 SEQ 题注编号。
5. **转 PDF**（必须走 docx 中转，保证版式和中文字体一致）：
   ```
   python "<SKILL_DIR>/scripts/convert_pdf.py" 报告名.docx
   ```
6. **自检**（必须）：
   ```
   python "<SKILL_DIR>/scripts/verify_output.py" 报告名.docx 报告名.pdf
   ```
7. **交付**：向用户报告两个文件的绝对路径 + 自检 JSON 结果（页数、图片数、字体、目录是否就绪）。有任何 check 失败：修复后重跑自检，再交付。

## 标准流程 B：课程答辩 / 汇报（pptx）

1. **从素材提炼大纲**：每页一个核心观点。推荐骨架：封面（题目/姓名/日期）→ 目录 → 背景/问题 → 方法（1-2 页）→ 实验/结果（图优先，1 页 1 图 1 结论）→ 总结 → 致谢/Q&A。
2. **构建 pptx**（二选一）：
   - **精细构建（默认）**：`mcp__ppt-server__create_presentation_from_template` 用 `assets/reference.pptx` 做模板，然后 `add_slide` + `populate_placeholder`/`add_bullet_points` 逐页填充，图表用 `add_chart`，图片用 `manage_image`。工具参数见 references/mcp-servers.md。
   - **快速稿**：`pandoc 笔记.md -o 答辩.pptx --reference-doc="<SKILL_DIR>/assets/reference.pptx"`，再人工校对版式。
3. **字体修复**（必须）：`python "<SKILL_DIR>/scripts/fix_pptx_fonts.py" 答辩.pptx`（标题黑体、正文微软雅黑，含主题字体修补）。
4. **自检**（必须）：`python "<SKILL_DIR>/scripts/verify_output.py" 答辩.pptx` —— 会逐页统计文字量，超过阈值报"大段文字"警告，此时把该页文字压缩成要点或移到备注。
5. **交付**：报告文件绝对路径 + 页数/图片数/每页字数检查结果。

PPT 内容规范（写大纲时遵守）：学术汇报风格；一页一个核心观点；图优先——有图就不放重复文字；每页正文 ≤ 60 个汉字的要点（3-5 条 bullet），完整句子放演讲备注；不要整段粘贴文字。

## 格式规范（构建与检查的依据）

**Word**（数值唯一权威来源：`scripts/style_config.py`；样式细则见 references/word-recipe.md）：
- 页面：A4，页边距上 2.5 / 下 2.5 / 左 3.0 / 右 2.5 cm；页眉"天津大学本科课程/科研报告"（随样式变化），页脚 `- 页码 -`（PAGE 域）
- 标题黑体加粗左对齐（一级三号 16pt、二级四号 14pt、三级小四 12pt，均为黑色非 Word 默认蓝）；文档主标题黑体小二居中；正文宋体小四 12pt，西文/数字 Times New Roman
- 正文段落：首行缩进 2 字符、1.5 倍行距、段前 0、段后 6pt
- 一二三级标题自动编号（`1`、`1.1`、`1.1.1`，默认 3 级）；自动目录（TOC 域，打开时自动更新；目录标题黑体三号、条目宋体小四）
- 图片自动缩放至版心宽；图片、表格自动编号（SEQ 域："图 N"下方 / "表 N"上方，五号宋体居中）
- 参考文献：GB/T 7714 排版（五号宋体、[n] 编号、悬挂缩进；"参考文献"章节后自动识别）
- 三种文档类型：`--style academic_paper | course_report | competition_report`
- 只用标准样式名与标准域代码，保证 WPS 打开无异常

**PDF**：由 docx 经 Word/WPS COM 导出，保持 docx 版式与中文字体。**禁止**直接 md→pdf（LaTeX 路径中文易乱码且版式与 docx 不一致）。

**PPT**：见上面内容规范；字体标题黑体、正文微软雅黑。

## 环境与故障排查

- 本机已验证可用：pandoc 3.11（`C:\Users\FAJ\AppData\Local\Pandoc\pandoc.exe`）、uvx、MS Word COM、WPS COM、python-docx/python-pptx/pypdf/pywin32。
- MCP 连接状态、各服务器配置与已知坑（如 ppt-server 必须带 `--with "mcp<2"`）见 references/mcp-servers.md。
- MCP 工具全部不可用时：直接用 pandoc CLI + 本 Skill 脚本，全流程不依赖 MCP，产物标准不变。
- 脚本报 `ModuleNotFoundError` 时：`pip install python-docx python-pptx pypdf pywin32`。
- 排查 MCP 服务器本身：`python "<SKILL_DIR>/scripts/mcp_probe.py" --config <配置json>` 可独立握手并列出工具。
