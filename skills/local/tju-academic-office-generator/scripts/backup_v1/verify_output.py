#!/usr/bin/env python3
"""交付前自动检查：docx / pdf / pptx。生成后必须跑，结果如实报告给用户。

检查项（对应用户规范）:
  docx : 能否打开 / 中文文本量 / eastAsia 字体覆盖率 / 目录域 / 标题编号 / 图片与"图 N"题注匹配 /
         表格与"表 N"题注匹配 / 是否含内容控件(SDT，WPS 兼容风险)
  pdf  : 能否打开 / 页数 / 首页中文可提取 / 内嵌字体含 CJK 字体
  pptx : 能否打开 / 页数 / 图片数 / 逐页字数(大段文字警告) / eastAsia 字体覆盖率

用法:
    python verify_output.py 文件1.docx 文件2.pdf 文件3.pptx [--max-slide-chars 100]

输出: 每个文件一行 JSON {"file","type","ok","checks":[{name,pass,detail}]}；
全部通过退出码 0，任一失败 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CJK_FONT_RE = re.compile(
    r"(SimSun|SimHei|SimXi|SimFang|KaiTi|FangSong|YaHei|YaHeiUI|宋体|黑体|楷体|仿宋|雅黑"
    r"|Song|Hei|Kai|Fang|Ming|CJK|GBK|NotoSansCJK|NotoSerifCJK|SourceHan)", re.I)


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "pass": bool(passed), "detail": detail}


# ---------------------------------------------------------------- docx
def check_docx(path: str, strict_captions: bool = True) -> dict:
    checks: list[dict] = []
    try:
        from docx import Document
        doc = Document(path)
    except Exception as exc:
        return {"file": path, "type": "docx", "ok": False,
                "checks": [_check("open_ok", False, f"{type(exc).__name__}: {exc}")]}

    checks.append(_check("open_ok", True, "python-docx 解析成功"))

    texts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                texts.append(cell.text)
    cjk = sum(len(CJK_RE.findall(t)) for t in texts)
    checks.append(_check("cjk_text", cjk > 0, f"中文字符 {cjk} 个"))

    # eastAsia 字体覆盖率（含中文的 run 中已显式设置 eastAsia 的比例）
    total = fixed = 0
    doc_xml = doc.element.body.xml
    for p in doc.paragraphs:
        for run in p.runs:
            if run.text and CJK_RE.search(run.text):
                total += 1
                rpr = run._r.find(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
                if rpr is not None:
                    rf = rpr.find(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts")
                    if rf is not None and rf.get(
                            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia"):
                        fixed += 1
    if total == 0:
        checks.append(_check("eastasia_fonts", "docDefaults" in (doc.styles.element.xml or ""),
                             "正文无含中文 run；依赖样式/文档默认字体"))
    else:
        pct = round(100 * fixed / total)
        checks.append(_check("eastasia_fonts", pct >= 80, f"含中文 run 的 eastAsia 覆盖率 {pct}% ({fixed}/{total})"))

    toc_ok = "TOC" in doc_xml and "instrText" in doc_xml
    checks.append(_check("toc_field", toc_ok, "存在" if toc_ok else "无目录域（如为无目录的短文档可忽略）"))

    numbered, unnumbered = [], []
    for p in doc.paragraphs:
        try:
            name = p.style.name if p.style is not None else ""
        except Exception:
            continue
        if name in ("Heading 1", "Heading 2") and p.text.strip():
            (numbered if re.match(r"^\s*\d", p.text) else unnumbered).append(p.text.strip()[:20])
    if numbered or not unnumbered:
        checks.append(_check("heading_numbering", True,
                             f"已编号 {len(numbered)} 个一二级标题" + (f"；未编号 {len(unnumbered)} 个" if unnumbered else "")))
    else:
        checks.append(_check("heading_numbering", False, f"一二级标题均未编号，如：{unnumbered[:3]}"))

    images = len(doc.inline_shapes)
    fig_caps = doc_xml.count("SEQ 图")
    tab_caps = doc_xml.count("SEQ 表")
    tables = len(doc.tables)
    if images == 0:
        checks.append(_check("figure_captions", True, "无图片"))
    else:
        ok = fig_caps == images
        checks.append(_check("figure_captions", ok if strict_captions else True,
                             f"图片 {images} 张，图题注 {fig_caps} 个" + ("" if ok else "（数量不匹配）")))
    if tables == 0:
        checks.append(_check("table_captions", True, "无表格"))
    else:
        ok = tab_caps == tables
        checks.append(_check("table_captions", ok if strict_captions else True,
                             f"表格 {tables} 个，表题注 {tab_caps} 个" + ("" if ok else "（数量不匹配）")))

    sdt = doc_xml.count("<w:sdt>")
    checks.append(_check("wps_compat", sdt == 0, "无内容控件(SDT)" if sdt == 0 else f"发现 {sdt} 个内容控件，WPS 兼容风险"))

    return {"file": path, "type": "docx", "ok": all(c["pass"] for c in checks), "checks": checks}


# ---------------------------------------------------------------- pdf
def check_pdf(path: str) -> dict:
    checks: list[dict] = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
    except Exception as exc:
        return {"file": path, "type": "pdf", "ok": False,
                "checks": [_check("open_ok", False, f"{type(exc).__name__}: {exc}")]}
    checks.append(_check("open_ok", True, f"共 {len(reader.pages)} 页"))

    fonts: set[str] = set()
    for page in reader.pages:
        try:
            res = page.get("/Resources", {})
            for f in (res.get("/Font", {}) or {}).values():
                obj = f.get_object()
                name = str(obj.get("/BaseFont", ""))
                if name:
                    fonts.add(name.split("+")[-1])
        except Exception:
            continue
    cjk_fonts = [f for f in fonts if CJK_FONT_RE.search(f)]
    checks.append(_check("cjk_fonts", bool(cjk_fonts),
                         f"内嵌 CJK 字体: {sorted(set(cjk_fonts))[:4]}" if cjk_fonts else f"未检出 CJK 字体（全部字体: {sorted(fonts)[:6]}）"))

    sample = ""
    for page in reader.pages[:3]:
        try:
            sample = page.extract_text() or ""
        except Exception:
            sample = ""
        if CJK_RE.search(sample):
            break
    checks.append(_check("cjk_text", bool(CJK_RE.search(sample)),
                         "中文可正常提取" if CJK_RE.search(sample) else "前 3 页未提取到中文，可能字体/编码异常"))

    return {"file": path, "type": "pdf", "ok": all(c["pass"] for c in checks), "checks": checks}


# ---------------------------------------------------------------- pptx
def check_pptx(path: str, max_chars: int) -> dict:
    checks: list[dict] = []
    try:
        from pptx import Presentation
        prs = Presentation(path)
    except Exception as exc:
        return {"file": path, "type": "pptx", "ok": False,
                "checks": [_check("open_ok", False, f"{type(exc).__name__}: {exc}")]}
    checks.append(_check("open_ok", True, f"共 {len(prs.slides)} 页"))

    total_chars = 0
    heavy: list[str] = []
    images = 0
    runs_total = runs_ea = 0

    def walk(shapes, idx: int):
        nonlocal total_chars, images, runs_total, runs_ea
        for shape in shapes:
            if shape.shape_type == 6:
                walk(shape.shapes, idx)
                continue
            if shape.shape_type == 13:  # PICTURE
                images += 1
            if not getattr(shape, "has_text_frame", False):
                continue
            page_text = ""
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    page_text += run.text
                    if run.text and CJK_RE.search(run.text):
                        runs_total += 1
                        rpr = run._r.find(
                            "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
                        if rpr is not None and rpr.find(
                                "{http://schemas.openxmlformats.org/drawingml/2006/main}ea") is not None:
                            runs_ea += 1
            page_chars = len(CJK_RE.findall(page_text)) + len(re.findall(r"[A-Za-z]+", page_text))
            if page_chars > max_chars:
                heavy.append(f"第{idx}页约{page_chars}字")
            total_chars += page_chars

    for i, slide in enumerate(prs.slides, start=1):
        walk(slide.shapes, i)
    checks.append(_check("slide_density", not heavy,
                         "每页文字量正常" if not heavy else f"大段文字警告: {'; '.join(heavy)}（应压缩为要点，完整内容移到演讲备注）"))
    checks.append(_check("images", True, f"图片/图表对象 {images} 个，全篇文字量约 {total_chars} 字"))
    pct = round(100 * runs_ea / runs_total) if runs_total else 100
    checks.append(_check("eastasia_fonts", pct >= 80,
                         f"含中文 run 的 eastAsia 覆盖率 {pct}%" + ("" if pct >= 80 else "（先运行 fix_pptx_fonts.py）")))
    return {"file": path, "type": "pptx", "ok": all(c["pass"] for c in checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+")
    parser.add_argument("--max-slide-chars", type=int, default=100)
    ns = parser.parse_args()

    all_ok = True
    for path in ns.files:
        lower = path.lower()
        if lower.endswith(".docx"):
            report = check_docx(path)
        elif lower.endswith(".pdf"):
            report = check_pdf(path)
        elif lower.endswith(".pptx"):
            report = check_pptx(path, ns.max_slide_chars)
        else:
            report = {"file": path, "type": "?", "ok": False,
                      "checks": [_check("supported", False, "仅支持 docx/pdf/pptx")]}
        all_ok &= report["ok"]
        print(json.dumps(report, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
