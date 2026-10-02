# 中文 Word 学术规范与实现细节

本文是 `postprocess_docx.py` 与 `assets/reference.docx` 的依据，也是人工核对格式时的检查单。

> **v2.0 说明**：格式数值的唯一权威来源已是 `scripts/style_config.py`（academic_paper / course_report / competition_report 三种文档类型）；本文以下内容仍有效，但注意三点变化——① 标题编号默认 **3 级**（`1.1.1`）；② postprocess 新增页面设置（A4，边距上2.5/下2.5/左3.0/右2.5 cm）、页眉报告头、页脚 `- 页码 -`（PAGE 域）、标题字号/加粗/黑色强制、正文首行缩进 2 字符与 1.5 倍行距、图片版心适配、参考文献 GB/T 7714 排版（五号宋体、[n]、悬挂缩进）；③ 样式层 `firstLineChars` 优先于段落级 `firstLine`，凡需清零继承缩进处（表格/题注/文献）必须显式写 `firstLineChars="0"`。

## 样式表（reference.docx 已内置）

| 元素 | 中文字体(eastAsia) | 西文字体(latin) | 字号 | 其他 |
|---|---|---|---|---|
| Title 主标题 | 黑体 | Times New Roman | 二号 22pt | 居中、加粗 |
| Heading 1 | 黑体 | Times New Roman | 三号 16pt | 段前/段后 13pt/13pt |
| Heading 2 | 黑体 | Times New Roman | 四号 14pt | 段前/段后 13pt/6pt |
| Heading 3 | 黑体 | Times New Roman | 小四 12pt | 加粗 |
| Normal 正文 | 宋体 | Times New Roman | 小四 12pt | 1.5 倍行距、首行缩进 2 字符 |
| Caption / Image Caption / Table Caption | 宋体 | Times New Roman | 五号 10.5pt | 居中、加粗 |
| 表格内文字 | 宋体 | Times New Roman | 五号 10.5pt | — |

## 为什么必须设 eastAsia

OOXML 的 `w:rFonts` 有四个槽位：`ascii` / `hAnsi`（西文）、`eastAsia`（中文）、`cs`（复杂文种）。python-docx 的 `font.name = "宋体"` 只写 ascii/hAnsi，**中文字符回落到文档默认东亚字体**，导致"指定黑体不生效"。所以：

- 样式层：每个样式的 rPr/rFonts 同时写 `w:ascii`、`w:hAnsi`、`w:eastAsia`；
- docDefaults 层：`styles.xml` 的 `w:docDefaults/w:rPrDefault/w:rPr/w:rFonts` 也写 eastAsia；
- run 层：`postprocess_docx.py` 默认对**所有含中文的 run** 再写一次 eastAsia（run 级优先级最高，兜底保证显示正确）。

三层都设置后，Word 和 WPS 的显示一致，这是"WPS 兼容"的关键。

## 标题自动编号

- 实现：给 Heading 1 / Heading 2 段落文本加前缀 `1 `、`1.1 `（GB/T 7713 风格，数字后一个空格，不带点）。三级默认不编号（`--number-levels 3` 可开）。
- 幂等：已有 `^\d+(\.\d+)*\s` 前缀的标题跳过，重复运行不会变成 `1 1 引言`。
- 计数器遇新一级编号自动归零（1.2 之后的新 H1 记 2）。
- 为什么用文字前缀而不是 numbering.xml 多级列表：文字前缀在 Word/WPS/旧版 Office 完全一致，且能进入目录文本；多级列表 XML 在 WPS 上偶发编号重排。学校模板如强制要求"多级列表域编号"，需按模板改，此时不要跑 `--no-number` 之外的自定义。

## 目录（TOC 域）

- 插入位置：第一个 Heading 1 之前。内容为：
  - "目 录"标题段（黑体三号居中，**不用 Heading 样式**，避免目录索引自己）；
  - TOC 域段落：`TOC \o "1-3" \h \z \u`（1-3 级标题、超链接、隐藏 web 前导符、使用大纲级别）；
  - 域后分页符，正文另起一页。
- `settings.xml` 写入 `<w:updateFields w:val="true"/>`：Word 打开时提示"是否更新域"（选是即得页码）；WPS 通常静默自动更新。`convert_pdf.py` 转 PDF 前会用 COM 主动 `Fields.Update()`，所以 PDF 里页码总是正确的。
- 域中占位文本为"（目录将在打开文档时自动更新）"，打开更新后消失。

## 图表题注（SEQ 域）

- **图**：pandoc 把 `![图注](path)` 转成样式为 `Image Caption` 的段落（在图片下方）。后处理改写为：`图 { SEQ 图 \* ARABIC }  图注文字`，居中、五号、加粗。
- **表**：Markdown 写在表格正上方的 `表：xxx` 段落，被改写为 `表 { SEQ 表 \* ARABIC }  xxx`。
- SEQ 域意味着用户后续在 Word/WPS 里增删图表后按 F9（或打印/导出时）编号自动重排。
- 幂等：段落里已有 `SEQ` instrText 的跳过。

## WPS 兼容清单

只用以下特性，全部为 WPS 原生支持：标准内置样式名（Heading 1/2/3、Normal、Caption）、`TOC`/`SEQ`/`PAGE` 域、`updateFields` 设置、eastAsia 字体槽位。避免：内容控件(SDT)、自定义 XML、主题字体依赖、numbering 多级列表。

## postprocess_docx.py 用法

```bash
python postprocess_docx.py 报告.docx                    # 全默认：字体+编号+TOC+题注
python postprocess_docx.py 报告.docx --no-toc           # 不要目录
python postprocess_docx.py 报告.docx --number-levels 3  # 三级标题也编号
python postprocess_docx.py 报告.docx --heading-font 黑体 --body-font 宋体 --latin-font "Times New Roman"
```

输出 JSON 摘要（编号了几级标题、几个题注、TOC 是否插入），供向用户报告。脚本就地修改文件。
