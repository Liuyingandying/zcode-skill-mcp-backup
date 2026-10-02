#!/usr/bin/env python3
"""docx 中文学术后处理 v2.0：页面设置、页眉页脚、eastAsia 字体强制、标题样式与三级编号、
目录(TOC)域、图表 SEQ 题注、正文段落格式、GB/T 7714 参考文献排版、图片版心适配。

开源 Office MCP（python-docx 系）共同的盲区：只写 latin 字体槽位（中文回落默认字体）、
无 TOC 工具、无题注编号、不管页面与页眉页脚。本脚本用 Word/WPS 原生支持的标准域与
标准样式补齐，格式数值统一来自 style_config.py（v2.0 起为唯一权威来源）。

用法:
    python postprocess_docx.py 报告.docx                             # 全默认：academic_paper
    python postprocess_docx.py 报告.docx --style course_report      # 课程报告格式
    python postprocess_docx.py 报告.docx --no-toc --number-levels 3
    python postprocess_docx.py 报告.docx --heading-font 黑体 --body-font 宋体

约定（由 SKILL.md 规定上游写法）:
    - 图注:  pandoc 图片 `![图注](路径)` 生成的 Image Caption 段落，或紧贴图片的 "图：xxx" 段落
    - 表注:  表格正上方一行 "表：xxx"
    - 参考文献: "参考文献" 标题之后的段落；无 [n] 编号时自动补 [1][2]...
幂等: 重复运行不会二次编号/二次插目录/二次加页眉页脚。

输出 JSON 摘要；就地修改文件。退出码: 成功 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from style_config import STYLE_NAMES, resolve_style_args  # noqa: E402

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
NUM_PREFIX_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\s.、]+")
REF_NUM_RE = re.compile(r"^\[\d+\]")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
BLACK = RGBColor(0, 0, 0)

BODY_STYLE_NAMES = ("Body Text", "First Paragraph")   # pandoc 正文段落样式
COMPACT_STYLE_NAME = "Compact"                        # 表格单元格 / 紧凑列表


def set_rfonts(rpr, ea: str | None, latin: str | None) -> None:
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    if latin:
        rfonts.set(qn("w:ascii"), latin)
        rfonts.set(qn("w:hAnsi"), latin)
    if ea:
        rfonts.set(qn("w:eastAsia"), ea)
        # hint=eastAsia：弯引号（U+201C/201D）、破折号等脚本歧义字符改用中文字体渲染，
        # 否则 Word 会按西文字体出半角形状，导致中文引号方向/形态错误（v2.0.1）
        rfonts.set(qn("w:hint"), "eastAsia")


def style_is_heading(name: str) -> bool:
    return name.startswith("Heading") or name in ("Title", "TOC Heading")


def _style_rpr(style):
    try:
        style.font.name = "Times New Roman"  # 确保 rPr 存在并写 ascii/hAnsi
    except Exception:
        return None
    return style.element.find(qn("w:rPr"))


def _set_run_font(run, ea: str, latin: str, size_pt: float | None = None) -> None:
    run.font.name = latin
    rpr = run._r.get_or_add_rPr()
    set_rfonts(rpr, ea, latin)
    # hint 仅对含中文的 run 生效：纯西文 run 不需要歧义标点改道（如 world's 的 ’），
    # 否则撇号/引号会按中文字体渲染变宽（v2.0.1）
    if ea and CJK_RE.search(run.text or ""):
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is not None:
            rfonts.set(qn("w:hint"), "eastAsia")
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    run.font.color.rgb = BLACK
    run.font.italic = False


def _set_first_line_chars(p: Paragraph, chars: int) -> None:
    """显式写段落级 w:ind@firstLineChars。

    OOXML 中 firstLineChars 优先于 firstLine，且样式层的 firstLineChars
    不会被段落级 firstLine=0 覆盖——表格/题注/参考文献要清零继承缩进时，
    必须在段落级也写 firstLineChars=0，否则 Body Text 样式的 2 字符缩进会泄漏。"""
    ind = p._p.get_or_add_pPr().get_or_add_ind()
    ind.set(qn("w:firstLineChars"), str(chars))


# ---------------------------------------------------------------- 页面设置（v2.0）
def _add_bottom_border(p: Paragraph) -> None:
    ppr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")       # 0.75pt
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "auto")
    pbdr.append(bottom)
    ppr.append(pbdr)


def setup_page(doc: Document, cfg: dict) -> dict:
    """A4 页面 + 页边距 + 页眉（校名报告头）+ 页脚页码（PAGE 域）。幂等。"""
    stats = {"page_set": False, "header": False, "footer_pagenum": False}
    page = cfg["page"]
    if doc.sections:
        sec = doc.sections[0]
        sec.page_width, sec.page_height = Cm(page["width_cm"]), Cm(page["height_cm"])
        sec.top_margin, sec.bottom_margin = Cm(page["margin_top_cm"]), Cm(page["margin_bottom_cm"])
        sec.left_margin, sec.right_margin = Cm(page["margin_left_cm"]), Cm(page["margin_right_cm"])
        stats["page_set"] = True

        # 页眉
        header = sec.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        if cfg["header_text"] not in hp.text:
            hp.text = ""
            run = hp.add_run(cfg["header_text"])
            _set_run_font(run, cfg["fonts"]["body_eastasia"], cfg["fonts"]["latin"], 10.5)
            hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            hp.paragraph_format.space_after = Pt(0)
            hp.paragraph_format.line_spacing = 1.0
            if hp._p.get_or_add_pPr().find(qn("w:pBdr")) is None:
                _add_bottom_border(hp)
            stats["header"] = True

        # 页脚页码：- N -（PAGE 域，打开/打印时自动准确）
        if cfg.get("footer_page_number", True):
            footer = sec.footer
            footer.is_linked_to_previous = False
            fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            if "PAGE" not in fp._p.xml:
                fp.text = ""
                fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                fp.paragraph_format.space_after = Pt(0)
                fp.paragraph_format.line_spacing = 1.0
                r1 = fp.add_run("- ")
                _fld_char_run(fp, "begin")
                _instr_run(fp, " PAGE \\* MERGEFORMAT ")
                _fld_char_run(fp, "separate")
                r2 = fp.add_run("1")
                _fld_char_run(fp, "end")
                r3 = fp.add_run(" -")
                for r in (r1, r2, r3):
                    _set_run_font(r, cfg["fonts"]["body_eastasia"], cfg["fonts"]["latin"], 10.5)
                stats["footer_pagenum"] = True
    return stats


# ---------------------------------------------------------------- 字体
def apply_fonts(doc: Document, heading_font: str, body_font: str, latin: str) -> dict:
    stats = {"styles_touched": 0, "runs_cjk": 0, "runs_cjk_fixed": 0}

    # 1) 文档默认字体（docDefaults）：决定没有显式字体时的回落
    styles_el = doc.styles.element
    dd_rpr = styles_el.find(qn("w:docDefaults") + "/" + qn("w:rPrDefault") + "/" + qn("w:rPr"))
    if dd_rpr is None:
        dd = styles_el.find(qn("w:docDefaults"))
        if dd is not None:
            dd_rpr = OxmlElement("w:rPr")
            dd.append(dd_rpr)
    if dd_rpr is not None:
        set_rfonts(dd_rpr, body_font, latin)
        if dd_rpr.find(qn("w:lang")) is None:  # 文档语言 zh-CN：歧义标点按东亚排版解析
            lang = OxmlElement("w:lang")
            lang.set(qn("w:eastAsia"), "zh-CN")
            dd_rpr.append(lang)

    # 2) 样式层：标题类样式给标题字体，其余给正文字体
    for style in doc.styles:
        if style.type not in (WD_STYLE_TYPE.PARAGRAPH, WD_STYLE_TYPE.CHARACTER):
            continue
        ea = heading_font if style_is_heading(style.name) else body_font
        rpr = _style_rpr(style)
        if rpr is not None:
            set_rfonts(rpr, ea, latin)
            stats["styles_touched"] += 1

    # 3) run 层兜底：所有含中文的 run 显式写 eastAsia（优先级最高，保证显示）
    def fix_runs(paragraphs):
        for p in paragraphs:
            heading = False
            try:
                heading = style_is_heading(p.style.name) if p.style is not None else False
            except Exception:
                pass
            for run in p.runs:
                if not run.text or not CJK_RE.search(run.text):
                    continue
                stats["runs_cjk"] += 1
                rpr = run._r.get_or_add_rPr()
                set_rfonts(rpr, heading_font if heading else body_font, latin)
                stats["runs_cjk_fixed"] += 1

    fix_runs(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                fix_runs(cell.paragraphs)
    return stats


# ---------------------------------------------------------------- 标题样式（v2.0）
def apply_heading_styles(doc: Document, cfg: dict) -> dict:
    """黑体 + 规定字号 + 加粗 + 黑色 + 左对齐 + 段间距；Title 黑体小二居中。"""
    stats = {"heading_styles_set": 0}
    latin = cfg["fonts"]["latin"]
    hei = cfg["fonts"]["heading_eastasia"]
    for level in (1, 2, 3):
        try:
            style = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        hcfg = cfg[f"heading{level}"]
        rpr = _style_rpr(style)
        if rpr is None:
            continue
        set_rfonts(rpr, hei, latin)
        style.font.size = Pt(hcfg["size_pt"])
        style.font.bold = hcfg["bold"]
        style.font.italic = False
        try:
            style.font.color.rgb = BLACK
        except Exception:
            pass
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(hcfg["space_before_pt"])
        pf.space_after = Pt(hcfg["space_after_pt"])
        pf.line_spacing = 1.5
        pf.keep_with_next = True
        pf.first_line_indent = Pt(0)
        stats["heading_styles_set"] += 1

    try:  # 文档主标题
        title = doc.styles["Title"]
        rpr = _style_rpr(title)
        if rpr is not None:
            set_rfonts(rpr, hei, latin)
            title.font.size = Pt(cfg["title"]["size_pt"])
            title.font.bold = cfg["title"]["bold"]
            title.font.italic = False
            try:
                title.font.color.rgb = BLACK
            except Exception:
                pass
            title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.paragraph_format.space_after = Pt(18)
            stats["heading_styles_set"] += 1
    except KeyError:
        pass
    return stats


# ---------------------------------------------------------------- 正文段落格式（v2.0）
def apply_body_paragraph_format(doc: Document, cfg: dict) -> dict:
    """Body Text / First Paragraph：首行缩进 2 字符、1.5 倍行距、段前 0、段后 6pt；
    Normal 定为小四宋体基准（TOC 条目等继承）；Compact 段落归零首行缩进。"""
    stats = {"body_styles_set": 0, "compact_fixed": 0}
    body = cfg["body"]
    for name in BODY_STYLE_NAMES:
        try:
            style = doc.styles[name]
        except KeyError:
            continue
        pf = style.paragraph_format
        pf.line_spacing = body["line_spacing"]
        pf.space_before = Pt(body["space_before_pt"])
        pf.space_after = Pt(body["space_after_pt"])
        pf.first_line_indent = Pt(body["size_pt"] * body["first_line_indent_chars"])  # 兜底
        ppr = style.element.get_or_add_pPr()
        ind = ppr.find(qn("w:ind"))
        if ind is not None:
            ind.set(qn("w:firstLineChars"), str(int(body["first_line_indent_chars"] * 100)))
        stats["body_styles_set"] += 1

    try:  # Normal 基准字号（TOC 条目等未显式设字号的段落继承）
        doc.styles["Normal"].font.size = Pt(body["size_pt"])
    except KeyError:
        pass

    try:  # Compact（表格单元格/紧凑列表）样式级清零缩进，阻断 Body Text 继承
        compact = doc.styles[COMPACT_STYLE_NAME]
        compact.paragraph_format.first_line_indent = Pt(0)
        compact.element.get_or_add_pPr().get_or_add_ind().set(qn("w:firstLineChars"), "0")
    except KeyError:
        pass

    for p in doc.paragraphs:  # 表格单元格/紧凑列表不吃正文缩进（段落级兜底）
        try:
            if p.style is not None and p.style.name == COMPACT_STYLE_NAME:
                p.paragraph_format.first_line_indent = Pt(0)
                _set_first_line_chars(p, 0)
                stats["compact_fixed"] += 1
        except Exception:
            continue
    return stats


# ---------------------------------------------------------------- 标题编号
def number_headings(doc: Document, max_level: int) -> dict:
    counters = {1: 0, 2: 0, 3: 0}
    numbered = 0
    for p in doc.paragraphs:
        try:
            name = p.style.name if p.style is not None else ""
        except Exception:
            continue
        m = re.match(r"^Heading ([1-3])$", name)
        if not m:
            continue
        level = int(m.group(1))
        if level > max_level:
            continue
        text = p.text.strip()
        if not text:
            continue
        existing = NUM_PREFIX_RE.match(text)
        if existing:
            parts = [int(x) for x in existing.group(1).split(".")]
            for i, v in enumerate(parts, start=1):
                counters[i] = v
            continue
        counters[level] += 1
        for lower in range(level + 1, 4):
            counters[lower] = 0
        num = ".".join(str(counters[i]) for i in range(1, level + 1))
        target = next((r for r in p.runs if r.text), None)
        if target is None:
            continue
        target.text = f"{num} {target.text}"
        numbered += 1
    return {"headings_numbered": numbered}


# ---------------------------------------------------------------- 目录域
def _fld_char_run(p: Paragraph, kind: str) -> None:
    run = p.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), kind)
    if kind == "begin":
        fld.set(qn("w:dirty"), "true")
    run._r.append(fld)


def _instr_run(p: Paragraph, code: str) -> None:
    run = p.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(XML_SPACE, "preserve")
    instr.text = code
    run._r.append(instr)


def apply_toc_styles(doc: Document, cfg: dict) -> int:
    """TOC 1/2/3 与 TOC Heading：宋体小四、黑色（样式缺失时跳过，靠 Normal 继承）。"""
    latin = cfg["fonts"]["latin"]
    song = cfg["fonts"]["body_eastasia"]
    touched = 0
    for name in ("TOC 1", "TOC 2", "TOC 3", "TOC Heading"):
        try:
            style = doc.styles[name]
        except KeyError:
            continue
        rpr = _style_rpr(style)
        if rpr is None:
            continue
        set_rfonts(rpr, song, latin)
        style.font.size = Pt(cfg["toc"]["body_size_pt"])
        style.font.bold = False
        try:
            style.font.color.rgb = BLACK
        except Exception:
            pass
        touched += 1
    return touched


def insert_toc(doc: Document, cfg: dict) -> dict:
    toc_levels = cfg["toc"]["levels"]
    body_xml = doc.element.body.xml
    if "TOC" in body_xml and "instrText" in body_xml:
        return {"toc_inserted": False, "toc_note": "已存在目录域，跳过"}
    first_heading = next(
        (p for p in doc.paragraphs
         if p.style is not None and p.style.name.startswith("Heading")), None)
    if first_heading is None:
        return {"toc_inserted": False, "toc_note": "未找到 Heading 样式段落，跳过"}

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("目  录")
    _set_run_font(run, cfg["fonts"]["heading_eastasia"], cfg["fonts"]["latin"],
                  cfg["toc"]["title_size_pt"])
    run.font.bold = True
    title.paragraph_format.space_after = Pt(12)
    first_heading._p.addprevious(title._p)

    field = doc.add_paragraph()
    _fld_char_run(field, "begin")
    _instr_run(field, f' TOC \\o "{toc_levels}" \\h \\z \\u ')
    _fld_char_run(field, "separate")
    field.add_run("（目录将在打开文档时自动更新）")
    _fld_char_run(field, "end")
    first_heading._p.addprevious(field._p)

    pagebreak = doc.add_paragraph()
    br_run = pagebreak.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    br_run._r.append(br)
    first_heading._p.addprevious(pagebreak._p)

    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "true")
        settings.append(upd)
    return {"toc_inserted": True, "toc_levels": toc_levels,
            "toc_styles_touched": apply_toc_styles(doc, cfg)}


# ---------------------------------------------------------------- 图表题注
def _clear_paragraph(p: Paragraph) -> None:
    for child in list(p._p):
        if child.tag in (qn("w:r"), qn("w:hyperlink")):
            p._p.remove(child)


def _add_seq_field(p: Paragraph, seq_name: str) -> None:
    _fld_char_run(p, "begin")
    _instr_run(p, f" SEQ {seq_name} \\* ARABIC ")
    _fld_char_run(p, "separate")
    p.add_run("1")
    _fld_char_run(p, "end")


def _has_seq(p: Paragraph) -> bool:
    return "instrText" in p._p.xml and "SEQ" in p._p.xml


def _format_caption(p: Paragraph, cfg: dict) -> None:
    """五号宋体、居中、加粗、无缩进（v2.0：字号/字体/颜色显式控制）。"""
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    _set_first_line_chars(p, 0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.0
    for run in p.runs:
        _set_run_font(run, cfg["fonts"]["body_eastasia"], cfg["fonts"]["latin"],
                      cfg["caption"]["size_pt"])
        run.font.bold = True


def _rewrite_caption(p: Paragraph, prefix: str, label: str, cfg: dict) -> None:
    _clear_paragraph(p)
    p.add_run(f"{prefix} ")
    _add_seq_field(p, prefix)
    p.add_run(f"  {label}")
    _format_caption(p, cfg)


def number_captions(doc: Document, cfg: dict) -> dict:
    stats = {"fig_captions": 0, "table_captions": 0}
    body = doc.element.body
    children = list(body.iterchildren())
    para_cache: dict[int, Paragraph] = {}

    def as_para(el) -> Paragraph | None:
        if el.tag != qn("w:p"):
            return None
        key = id(el)
        if key not in para_cache:
            para_cache[key] = Paragraph(el, doc)
        return para_cache[key]

    has_drawing = lambda el: el is not None and el.find(".//" + qn("w:drawing")) is not None

    # 先处理表注："表：xxx" 段落且后随表格
    for i, el in enumerate(children):
        p = as_para(el)
        if p is None or _has_seq(p):
            continue
        text = p.text.strip()
        if not re.match(r"^表[：:]", text):
            continue
        nxt = children[i + 1] if i + 1 < len(children) else None
        if nxt is not None and nxt.tag == qn("w:tbl"):
            _rewrite_caption(p, "表", re.sub(r"^表[：:]\s*", "", text), cfg)
            p.paragraph_format.keep_with_next = True  # 题注与表格不分离
            stats["table_captions"] += 1

    # 再处理图注：a) Caption 样式段落（pandoc 图片题注）；b) 紧贴图片的 "图：xxx" 段落
    for i, el in enumerate(children):
        p = as_para(el)
        if p is None or _has_seq(p):
            continue
        text = p.text.strip()
        if text.startswith("表"):
            continue
        prev = children[i - 1] if i > 0 else None
        style_name = ""
        try:
            style_name = p.style.name if p.style is not None else ""
        except Exception:
            pass
        is_caption_style = "Caption" in style_name and bool(text)
        is_fig_marker = bool(re.match(r"^图[：:]", text)) and has_drawing(prev)
        if is_caption_style or is_fig_marker:
            label = re.sub(r"^图[：:]\s*", "", text)
            _rewrite_caption(p, "图", label, cfg)
            if has_drawing(prev):  # 图片与其下方图注不分离
                prev_para = as_para(prev)
                if prev_para is not None:
                    prev_para.paragraph_format.keep_with_next = True
            stats["fig_captions"] += 1

    # 兜底：所有含图片的段落与后续内容保持同页（图片通常紧跟图注）
    for el in children:
        if el.tag == qn("w:p") and has_drawing(el):
            p = as_para(el)
            if p is not None:
                p.paragraph_format.keep_with_next = True
    return stats


# ---------------------------------------------------------------- 图片版心适配（v2.0）
def fit_images(doc: Document, cfg: dict) -> dict:
    """超出版心宽度的图片等比缩到版心宽（pandoc 按原图像素嵌入，大图会溢出页面）。"""
    stats = {"images_fit": 0, "images_total": len(doc.inline_shapes)}
    if not doc.sections:
        return stats
    sec = doc.sections[0]
    content_emu = int(sec.page_width - sec.left_margin - sec.right_margin)
    for shape in doc.inline_shapes:
        try:
            if shape.width > content_emu:
                ratio = content_emu / shape.width
                shape.height = int(shape.height * ratio)
                shape.width = int(shape.width * ratio)
                stats["images_fit"] += 1
        except Exception:
            continue
    return stats


EMU_PER_TWIP = 635  # 1 twip = 635 EMU


def _tblpr_insert_tblw(tblpr, tblw) -> None:
    """w:tblW 在 tblPr 里有固定次序（须在 jc/tblLayout/tblLook 之前）。"""
    later_tags = ("w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders",
                  "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook")
    for tag in later_tags:
        anchor = tblpr.find(qn(tag))
        if anchor is not None:
            anchor.addprevious(tblw)
            return
    tblpr.append(tblw)


def polish_tables(doc: Document, cfg: dict) -> dict:
    """表格字号统一为五号，按内容实测宽度定列宽、居中；单元格单倍行距零段距（v2.0）。

    pandoc 按 Markdown 源码字符数写死列宽（tblGrid/tcW），中文表头会被压成
    两行且与垂直居中的相邻列形成阶梯错位。这里：
      1) 表内文字设为五号（学术规范，也显著降低列宽压力）；
      2) 按 10.5pt 字符渲染宽度估算每列所需宽度（CJK/全角≈210 twips、
         字母数字≈118、其他≈105）+ 单元格边距，再留 12% 余量；
      3) 总宽不超版心则直接采用（单行零折行），超了等比收缩。
    显式写死宽度（Word 的 autofit 在 COM 导出时不可靠）。
    """
    stats = {"tables_polished": 0}
    content_twips = None
    if doc.sections:
        sec = doc.sections[0]
        content_twips = int((sec.page_width - sec.left_margin - sec.right_margin) / EMU_PER_TWIP)

    def est_twips(text: str) -> int:
        w = 0
        for ch in text:
            if ord(ch) > 0x2E7F:      # CJK / 全角标点 @10.5pt
                w += 210
            elif ch == " ":
                w += 62
            elif ch.isalnum():
                w += 118
            else:
                w += 105
        return w

    CELL_MARGINS = 260   # 单元格左右边距合计（twips）
    SAFETY = 1.12        # 列宽余量，避免 Word 两端对齐时临界折行
    MIN_COL = 900

    for table in doc.tables:
        try:
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            n_cols = len(table.columns)
            if n_cols == 0 or content_twips is None:
                continue
            # 表内文字统一五号；清零首行缩进；单倍行距、零段距（v2.0：
            # Compact 继承 Body Text 的 1.5 倍行距/6pt 段后，会把表格撑高）
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.first_line_indent = Pt(0)
                        _set_first_line_chars(p, 0)
                        p.paragraph_format.line_spacing = 1.0
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(0)
                        for run in p.runs:
                            run.font.size = Pt(cfg["table"]["cell_size_pt"])

            required = [0] * n_cols
            for row in table.rows:
                cells = row.cells
                if len(cells) != n_cols:
                    continue
                for i, cell in enumerate(cells):
                    tw = min(int((est_twips(cell.text or "") + CELL_MARGINS) * SAFETY),
                             int(content_twips * 0.45))
                    required[i] = max(required[i], tw)
            required = [max(w, MIN_COL) for w in required]
            total = sum(required)
            if total <= content_twips:
                widths = required            # 每列单行放下，零折行
            else:
                widths = [max(int(w * content_twips / total), MIN_COL) for w in required]

            tbl = table._tbl
            grid = tbl.find(qn("w:tblGrid"))
            if grid is not None:
                for col_el, wd in zip(grid.findall(qn("w:gridCol")), widths):
                    col_el.set(qn("w:w"), str(wd))
            tblw = tbl.tblPr.find(qn("w:tblW"))
            if tblw is None:
                tblw = OxmlElement("w:tblW")
                _tblpr_insert_tblw(tbl.tblPr, tblw)
            tblw.set(qn("w:w"), str(sum(widths)))
            tblw.set(qn("w:type"), "dxa")
            for row in table.rows:
                cells = row.cells
                if len(cells) != n_cols:
                    continue
                for i, cell in enumerate(cells):
                    tcpr = cell._tc.get_or_add_tcPr()
                    tcw = tcpr.find(qn("w:tcW"))
                    if tcw is None:
                        tcw = OxmlElement("w:tcW")
                        tcpr.insert(0, tcw)  # tcW 在 tcPr 序列的最前部
                    tcw.set(qn("w:w"), str(widths[i]))
                    tcw.set(qn("w:type"), "dxa")
            table.autofit = False  # 固定布局，按上面写死的宽度渲染
            stats["tables_polished"] += 1
        except Exception:
            continue
    return stats


# ---------------------------------------------------------------- 参考文献（v2.0，GB/T 7714 排版）
def format_references(doc: Document, cfg: dict) -> dict:
    """"参考文献"标题之后、下一标题之前的段落：五号宋体、[n] 编号、悬挂缩进。"""
    stats = {"ref_sections": 0, "refs_formatted": 0, "refs_renumbered": 0}
    paras = doc.paragraphs
    ref_cfg = cfg["reference"]
    latin = cfg["fonts"]["latin"]
    song = cfg["fonts"]["body_eastasia"]

    start = None
    for i, p in enumerate(paras):
        try:
            style_name = p.style.name if p.style is not None else ""
        except Exception:
            continue
        if style_name.startswith("Heading") and "参考文献" in p.text:
            start = i + 1
            break
    if start is None:
        return stats

    refs = []
    for p in paras[start:]:
        try:
            style_name = p.style.name if p.style is not None else ""
        except Exception:
            break
        if style_name.startswith("Heading") or style_name == "Title":
            break
        if p.text.strip():
            refs.append(p)

    if not refs:
        return stats
    stats["ref_sections"] = 1

    if not any(REF_NUM_RE.match(p.text.strip()) for p in refs):  # 无 [n] 时自动补编号
        for i, p in enumerate(refs, start=1):
            target = next((r for r in p.runs if r.text), None)
            if target is not None:
                target.text = f"[{i}] {target.text.lstrip()}"
                stats["refs_renumbered"] += 1

    for p in refs:
        pf = p.paragraph_format
        pf.left_indent = Pt(ref_cfg["hanging_indent_pt"])
        pf.first_line_indent = Pt(-ref_cfg["hanging_indent_pt"])
        _set_first_line_chars(p, 0)  # 阻断 Body Text 的 2 字符缩进，保证悬挂生效
        pf.space_before = Pt(0)
        pf.space_after = Pt(ref_cfg["space_after_pt"])
        pf.line_spacing = ref_cfg["line_spacing"]
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            _set_run_font(run, song, latin, ref_cfg["size_pt"])
            run.font.bold = False
        stats["refs_formatted"] += 1
    return stats


# ---------------------------------------------------------------- 主流程
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docx", help="要处理的 docx 路径（就地修改）")
    parser.add_argument("--style", default="academic_paper", choices=list(STYLE_NAMES),
                        help="文档类型样式（v2.0）")
    parser.add_argument("--heading-font", default=None, help="覆盖样式配置的标题字体")
    parser.add_argument("--body-font", default=None, help="覆盖样式配置的正文字体")
    parser.add_argument("--latin-font", default=None, help="覆盖样式配置的西文字体")
    parser.add_argument("--number-levels", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--toc-levels", default=None)
    parser.add_argument("--no-page-setup", action="store_true", help="跳过页面/页眉/页脚")
    parser.add_argument("--no-fonts", action="store_true")
    parser.add_argument("--no-number", action="store_true")
    parser.add_argument("--no-toc", action="store_true")
    parser.add_argument("--no-captions", action="store_true")
    parser.add_argument("--no-references", action="store_true")
    ns = parser.parse_args()

    cfg = resolve_style_args(ns.style, ns.heading_font, ns.body_font, ns.latin_font)
    if ns.toc_levels:
        cfg["toc"]["levels"] = ns.toc_levels

    doc = Document(ns.docx)
    result: dict = {"file": ns.docx, "style": ns.style, "applied": [], "ok": True}
    try:
        # 顺序说明：页面先行（页眉页脚/版心宽度）；目录/题注/编号会新建 run，
        # 字体处理必须最后执行才能覆盖它们；表格/参考文献在字体前做段落级收尾。
        if not ns.no_page_setup:
            page = setup_page(doc, cfg)
            result["page"] = page
            result["applied"].append("page_setup")
            if page.get("header"):
                result["applied"].append("header")
            if page.get("footer_pagenum"):
                result["applied"].append("footer_pagenum")
        if not ns.no_toc:
            result["toc"] = insert_toc(doc, cfg)
            result["applied"].append("toc")
        if not ns.no_captions:
            result["captions"] = number_captions(doc, cfg)
            result["applied"].append("captions")
        result["images"] = fit_images(doc, cfg)
        result["applied"].append("images_fit")
        result["tables"] = polish_tables(doc, cfg)
        result["applied"].append("tables_autofit_center")
        if not ns.no_references:
            result["references"] = format_references(doc, cfg)
            result["applied"].append("references_gbt7714")
        result["heading_styles"] = apply_heading_styles(doc, cfg)
        result["applied"].append("heading_styles")
        result["body_format"] = apply_body_paragraph_format(doc, cfg)
        result["applied"].append("body_format")
        if not ns.no_number:
            result["numbering"] = number_headings(doc, ns.number_levels)
            result["applied"].append("heading_numbering")
        if not ns.no_fonts:
            stats = apply_fonts(doc, cfg["fonts"]["heading_eastasia"],
                                cfg["fonts"]["body_eastasia"], cfg["fonts"]["latin"])
            result["applied"].append("fonts")
            result["fonts"] = stats
        doc.save(ns.docx)
    except Exception as exc:  # 让上层看到真实失败原因
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
