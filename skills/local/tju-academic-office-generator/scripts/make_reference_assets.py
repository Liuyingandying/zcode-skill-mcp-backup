#!/usr/bin/env python3
"""生成本 Skill 的 assets/reference.docx 与 assets/reference.pptx。

以 pandoc 官方默认模板为底（保证 pandoc 与 python-docx/pptx 的样式名/版式名完全兼容），
改造为中文学术规范：标题黑体、正文宋体、西文 Times New Roman、A4、1.5 倍行距、
首行缩进 2 字符、题注样式；pptx 为 16:9、主题字体 黑体/微软雅黑。

用法: python make_reference_assets.py   （需要 pandoc 在 PATH）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation
from pptx.util import Emu, Inches

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "assets"))
sys.path.insert(0, SCRIPT_DIR)
from fix_pptx_fonts import patch_theme  # noqa: E402

BODY_LATIN = "Times New Roman"


def find_pandoc() -> str:
    found = shutil.which("pandoc")
    if found:
        return found
    for cand in (
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Pandoc", "pandoc.exe"),
        r"C:\Program Files\Pandoc\pandoc.exe",
    ):
        if cand and os.path.isfile(cand):
            return cand
    raise SystemExit("找不到 pandoc，请先安装或加入 PATH")


def pandoc_default(ext: str) -> str:
    """导出 pandoc 内置 reference 模板到临时文件。"""
    path = os.path.join(tempfile.gettempdir(), f"pandoc_default_reference.{ext}")
    with open(path, "wb") as fh:
        subprocess.run([find_pandoc(), "--print-default-data-file", f"reference.{ext}"],
                       check=True, stdout=fh)
    return path


def style_rpr(style):
    style.font.name = BODY_LATIN  # 确保 rPr 与 rFonts 存在
    return style.element.find(qn("w:rPr"))


def tune_style(doc: Document, name: str, *, ea: str, size: float | None = None,
               bold: bool | None = None, align=None, line=None, first_indent=None,
               space_before=None, space_after=None, color_black=False):
    try:
        st = doc.styles[name]
    except KeyError:
        return False
    if st.type not in (WD_STYLE_TYPE.PARAGRAPH, WD_STYLE_TYPE.CHARACTER):
        return False
    set_rfonts_local(style_rpr(st), ea)
    if size is not None:
        st.font.size = Pt(size)
    if bold is not None:
        st.font.bold = bold
    if color_black:
        try:
            st.font.color.rgb = RGBColor(0, 0, 0)
        except Exception:
            pass
    if st.type == WD_STYLE_TYPE.PARAGRAPH:
        pf = st.paragraph_format
        if align is not None:
            pf.alignment = align
        if line is not None:
            pf.line_spacing = line
        if first_indent is not None:
            pf.first_line_indent = first_indent
        if space_before is not None:
            pf.space_before = Pt(space_before)
        if space_after is not None:
            pf.space_after = Pt(space_after)
    return True


def set_rfonts_local(rpr, ea: str) -> None:
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), ea)


def make_docx(out_path: str) -> dict:
    doc = Document(pandoc_default("docx"))

    # A4 + 学术页边距
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.top_margin = section.bottom_margin = Cm(2.54)
        section.left_margin = section.right_margin = Cm(3.17)

    # 文档默认东亚字体 = 宋体
    styles_el = doc.styles.element
    dd_rpr = styles_el.find(qn("w:docDefaults") + "/" + qn("w:rPrDefault") + "/" + qn("w:rPr"))
    if dd_rpr is not None:
        set_rfonts_local(dd_rpr, "宋体")

    tuned = []
    spec = [
        # (样式名, 东亚字体, 字号pt, 加粗, 对齐, 行距, 首行缩进, 段前, 段后)
        ("Normal",          "宋体", 12, None, None, 1.5, None,      None, None),
        ("Body Text",       "宋体", 12, None, None, 1.5, Pt(24),    None, None),
        ("First Paragraph", "宋体", 12, None, None, 1.5, Pt(24),    None, None),
        ("Compact",         "宋体", 12, None, None, 1.5, Pt(0),     None, 3),
        ("Title",           "黑体", 22, True, WD_ALIGN_PARAGRAPH.CENTER, 1.5, None, 0, 12),
        ("Subtitle",        "黑体", 14, None, WD_ALIGN_PARAGRAPH.CENTER, 1.5, None, 0, 12),
        ("Heading 1",       "黑体", 16, True, None, 1.5, None,      13, 13),
        ("Heading 2",       "黑体", 14, True, None, 1.5, None,      13, 6),
        ("Heading 3",       "黑体", 12, True, None, 1.5, None,      6,  6),
        ("Heading 4",       "黑体", 12, True, None, 1.5, None,      6,  6),
        ("TOC Heading",     "黑体", 16, True, None, 1.5, None,      13, 13),
        ("Caption",         "宋体", 10.5, True, WD_ALIGN_PARAGRAPH.CENTER, 1.0, None, 3, 3),
        ("Image Caption",   "宋体", 10.5, True, WD_ALIGN_PARAGRAPH.CENTER, 1.0, None, 3, 3),
        ("Table Caption",   "宋体", 10.5, True, WD_ALIGN_PARAGRAPH.CENTER, 1.0, None, 3, 3),
        ("Block Text",      "宋体", 12, None, None, 1.5, None,      3, 3),
    ]
    for name, ea, size, bold, align, line, indent, sb, sa in spec:
        if tune_style(doc, name, ea=ea, size=size, bold=bold, align=align, line=line,
                      first_indent=indent, space_before=sb, space_after=sa, color_black=True):
            tuned.append(name)

    doc.save(out_path)
    return {"file": out_path, "styles_tuned": tuned}


def make_pptx(out_path: str) -> dict:
    import gc
    tmp = pandoc_default("pptx")
    prs = Presentation(tmp)  # pandoc 内置模板自带学术版式（Title Slide / Title and Content / Section Header...）
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)  # 16:9
    # 注意：不要改版式占位符几何——pandoc 对手改过的 layout XML 解析不稳定
    # （会把 slide 上的图形写成零尺寸）。图片铺满由 fix_pptx_fonts.py 的
    # fit_pictures 在生成后确定性完成。
    prs.save(out_path)
    del prs
    gc.collect()
    patched = patch_theme(out_path, title_font="黑体", body_font="微软雅黑")
    return {"file": out_path, "theme_patched": patched, "aspect": "16:9"}


def main() -> int:
    os.makedirs(ASSET_DIR, exist_ok=True)
    results = [
        make_docx(os.path.join(ASSET_DIR, "reference.docx")),
        make_pptx(os.path.join(ASSET_DIR, "reference.pptx")),
    ]
    import json
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
