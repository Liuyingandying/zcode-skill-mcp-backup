# 学术答辩 PPT 规范与实现细节

## 内容规范（写大纲时的硬规则）

1. **一页一个核心观点**。每页回答一个问题："这一页我想让评委记住什么？"
2. **图优先**：实验结果页放图表/截图，文字只留一句结论；能用图说的不用表，能用表说的不用段落。
3. **文字上限**：每页正文 ≤ 60 个汉字，3-5 条 bullet，每条一行以内。整段文字移到演讲者备注（pptx MCP 用 `populate_placeholder` 填 notes 或管理文本时说明）。`verify_output.py` 会逐页统计字数，>100 字报警告。
4. 骨架（15-20 分钟答辩约 12-18 页）：
   封面（题目/姓名/单位/日期）→ 目录 → 研究背景与问题（1-2 页）→ 相关工作（1 页，可选）→ 方法/方案（2-3 页）→ 实验与结果（3-5 页，图优先）→ 总结与展望（1 页）→ 致谢/Q&A（1 页）
5. 学院答辩通常要求出现：选题依据、创新点、工作量证明。数据必须来自用户素材，不许编造。

## 版式与字体

| 元素 | 规范 |
|---|---|
| 标题字体 | 黑体（eastAsia 强制） |
| 正文字体 | 微软雅黑（eastAsia 强制），西文/数字同字体或 Arial |
| 标题字号 | 页标题 28-32pt；正文 bullet ≥ 18pt（答辩教室后排要能看清） |
| 配色 | 白底 + 深蓝/校色标题栏，正深灰（#333），强调色一种；避免花哨模板 |
| 图片 | 占页面 1/2 以上时效果最好；`manage_image` 单位英寸，16:9 页面 13.33×7.5 in |

**字体机制**与 docx 同理：python-pptx 只写 latin 槽位，中文会回落。`fix_pptx_fonts.py` 做两层修补：
1. `ppt/theme/theme1.xml` 的 `majorFont`/`minorFont` 的 `<a:ea>` 与 `<a:latin>` typeface（主题层兜底）；
2. 所有含中文 run 的 rPr 写 `<a:ea>`（run 层强制），标题占位符用标题字体、正文用正文字体。

## pptx 工具选择

- **精细构建（默认）**：`create_presentation_from_template`（模板用 `assets/reference.pptx`：16:9、主题字体已设黑体/微软雅黑、深蓝学术风）→ 逐页 `add_slide` + `populate_placeholder`/`add_bullet_points` → `add_chart`（实验数据可视化）→ `manage_image` → `save_presentation` → `fix_pptx_fonts.py`。
- **快速稿**：`pandoc 笔记.md -o 答辩.pptx --reference-doc=reference.pptx`。pandoc 按二级标题分页、每页一个头滑+正文，适合文字型大纲；图表仍建议之后用 MCP 或 `manage_image` 补。
- 版式索引（`add_slide` 的 layout_index）取决于模板，可先 `get_template_file_info`/`list_slide_templates` 查。

## verify_output.py 对 pptx 的检查项

- 文件可正常打开（python-pptx 解析成功）
- 页数、总图片数
- 逐页字数（CJK 字符 + 英文单词），>100 字警告"大段文字，需要压缩"
- 中文字体覆盖率：含中文的 run 中已设 eastAsia 的比例（≥80% 通过；未通过先跑 fix_pptx_fonts.py）
