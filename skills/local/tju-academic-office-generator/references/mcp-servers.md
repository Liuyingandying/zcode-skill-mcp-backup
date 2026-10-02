# MCP 服务器参考手册

本 Skill 依赖的 3 个开源 MCP 服务器：已调研、已在本机验证（stdio 握手 + tools/list 成功）。调研日期 2026-09-17。

## 已验证的启动命令（ZCode 已按此配置）

| 服务器 | 启动命令 | 工具数 | 验证结果 |
|---|---|---|---|
| word-document-server | `E:\conda\Scripts\uvx.exe --from office-word-mcp-server word_mcp_server` | 54 | ✅ 握手成功 |
| ppt-server | `E:\conda\Scripts\uvx.exe --from office-powerpoint-mcp-server --with "mcp<2" ppt_mcp_server` | 37 | ✅ 握手成功 |
| pandoc | `E:\conda\Scripts\uvx.exe mcp-pandoc` | 1 (`convert-contents`) | ✅ 握手成功 |

### 关键坑（已踩过，勿重复）

1. **ppt-server 必须加 `--with "mcp<2"`**。上游声明 `mcp[cli]>=1.8.0` 无上界，uvx 会解析到 mcp 2.x，而其代码用旧 API（`from mcp.server.fastmcp import FastMCP`），启动即 `ModuleNotFoundError`。锁定 `mcp<2` 后正常。
2. **mcp-pandoc 依赖系统 pandoc**。本机已装 pandoc 3.11（`C:\Users\FAJ\AppData\Local\Pandoc\pandoc.exe`，已在用户 PATH）。
3. 首次 uvx 启动需下载依赖，可能 1-3 分钟，属正常；之后有缓存。

## word-document-server（Office-Word-MCP-Server）

- 仓库：https://github.com/GongRzhe/Office-Word-MCP-Server （2.1k★，MIT，**2026-03 已归档只读**，仍可正常安装使用；PyPI 包 `office-word-mcp-server`，底层 python-docx + FastMCP）

常用工具（完整 54 个见 probe 输出）：

| 工具 | 要点 |
|---|---|
| `create_document(filename, title?, author?)` | 新建 docx |
| `add_heading(filename, text, level, font_name?, font_size?, bold?)` | level 1-9 |
| `add_paragraph(filename, text, style?, font_name?, size?, bold?, italic?, color?, alignment?)` | color 是不带 # 的 hex |
| `add_picture(filename, image_path, width?)` | width 单位英寸；用绝对路径 |
| `add_table(filename, rows, cols, data?)` + `format_table*` / `merge_table_cells*` / `set_table_column_width*` / `highlight_table_header` / `apply_table_alternating_rows` | 表格工具最全（约 20 个） |
| `search_and_replace` / `format_text` / `create_custom_style` | 改文字/样式 |
| `add_footnote_to_document` 等脚注系列 | 学术脚注可用 |
| `get_document_text` / `get_document_outline` / `get_document_xml` | 读取检查 |
| `convert_to_pdf(doc_path, pdf_path?)` | Windows 仅走 docx2pdf→MS Word COM；无 Word 的机器会失败，此时改用本 Skill `convert_pdf.py`（含 WPS/soffice 降级） |

**已知能力缺口**（调研实测确认，不要指望它做）：
- **没有目录(TOC)工具**：源码里有 `add_table_of_contents` 函数但未注册为 MCP 工具，且其实现是静态文本重建、会丢图。
- **没有图表题注/SEQ 自动编号**。
- **不处理中文 eastAsia 字体**：`font_name` 只写 `w:rFonts` 的 ascii/hAnsi，中文回落默认字体。
- 以上三项全部由本 Skill `scripts/postprocess_docx.py` 补齐——docx 构建完成后必须跑一遍。

## ppt-server（Office-PowerPoint-MCP-Server）

- 仓库：https://github.com/GongRzhe/Office-PowerPoint-MCP-Server （1.9k★，MIT，2026-03 已归档；PyPI `office-powerpoint-mcp-server`，底层 python-pptx）

常用工具（完整 37 个）：

| 工具 | 要点 |
|---|---|
| `create_presentation_from_template(template_path, save_path)` | 用 .pptx/.potx 模板建稿，保留主题；可用本 Skill `assets/reference.pptx` |
| `add_slide(presentation_path, layout_index)` | 版式索引取决于模板 |
| `populate_placeholder` / `add_bullet_points` / `manage_text` | 填内容；manage_text 可设字号/颜色/加粗 |
| `manage_image(slide, image_path, left, top, width?, height?)` | 单位英寸 |
| `add_chart(type: column/bar/line/pie, categories, series)` + `update_chart_data` | 数据图 |
| `add_table` / `format_table_cell` | 表格 |
| `apply_professional_design` / `apply_picture_effects` | 一键设计/图片效果 |
| `extract_presentation_text` / `get_presentation_info` | 读取检查 |
| `save_presentation` | 保存 |

同样**不处理中文字体** → 跑 `scripts/fix_pptx_fonts.py`。模板目录可用 env `PPT_TEMPLATE_PATH` 扩展。

## pandoc（mcp-pandoc）

- 仓库：https://github.com/vivekVells/mcp-pandoc （580★，MIT，活跃）
- 唯一工具 `convert-contents`，参数：`contents` / `input_file` / `input_format` / `output_format` / `output_file`（docx/pdf/pptx 等二进制格式**必须给 output_file 绝对路径**）/ `reference_doc` / `defaults_file` / `filters`
- 支持方向：md/html/txt/docx/odt/rst/latex/epub/ipynb 互转；**pdf、pptx 仅可作为输出**
- `reference_doc` 只对 docx/odt/pptx 输出生效（样式来自参考文档，参考文档格式必须与输出一致）
- **md→pdf 需要 LaTeX（MiKTeX/TeX Live）**，本机未装且中文易乱码 → 一律走 docx 中转（本 Skill 流程 A 第 5 步）

等价 CLI（MCP 不可用时）：
```bash
# md → docx（学术样式）
pandoc 输入.md -o 输出.docx --reference-doc=reference.docx --resource-path=<图片目录>
# md → pptx 快速稿
pandoc 输入.md -o 输出.pptx --reference-doc=reference.pptx
```

## 模板填空（学校/单位发了 docx 模板时）

调研结论：用户提到的 "MCP-MD-PDF"（sham-devs/mcp-md-pdf，1★）**只做 md→docx/pdf 外观样式，不支持 docxtpl 占位符模板填充**，与"使用 docx 模板生成正式文件"的需求不符，故未接入。真正做模板填充的开源方案：

1. **docxtpl（python 库，Jinja2 语法）**——最可靠。模板里写 `{{姓名}}`、`{%for%}`，用几行 python-docx 生态代码填充。需要时让我现场写填充脚本即可（复用库，不是重造解析器）。
2. z1w2r3/doc-mcp（npx docxtpl-mcp，1★ 极早期）：有 `generate_document`/`list_templates` 等工具，风险自担，未默认接入。
3. 若模板只是"样式模板"（不是占位符填空）：把它改造/另存为 `reference.docx` 走 pandoc 管线更稳。

## ZCode 配置位置与排障

- 用户级 MCP 配置：`C:\Users\FAJ\.zcode\cli\config.json` → `mcp.servers`（本 Skill 的三个服务器已注册在此，新开会话生效）。
- 服务器连不上时：
  1. 用探针独立验证：`python "<SKILL_DIR>/scripts/mcp_probe.py" --config <json文件>`
  2. 检查 uvx 是否存在：`E:\conda\Scripts\uvx.exe --version`
  3. ppt-server 报 `No module named 'mcp.server.fastmcp'` → 配置里丢了 `--with mcp<2`
  4. pandoc 工具报 pandoc not found → 检查 `C:\Users\FAJ\AppData\Local\Pandoc\pandoc.exe`
- 修复 MCP 配置属于 `zcode-guide:diagnosing-mcp` 的范畴。
