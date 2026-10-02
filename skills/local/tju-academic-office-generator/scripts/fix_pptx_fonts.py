#!/usr/bin/env python3
"""pptx 中文字体修复：主题字体 + 全部含中文 run 的 eastAsia 槽位。

python-pptx 的 run.font.name 只写 latin 槽位，中文回落默认字体。本脚本：
  1. 修补 ppt/theme/theme1.xml：majorFont/minorFont 的 <a:ea> 与 <a:latin>（主题层兜底）；
  2. 遍历所有幻灯片文本：标题占位符 → 标题字体，其余 → 正文字体（run 层强制）。

用法:
    python fix_pptx_fonts.py 答辩.pptx
    python fix_pptx_fonts.py 答辩.pptx --title-font 黑体 --body-font 微软雅黑

输出 JSON 摘要；就地修改文件。退出码: 成功 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile

from pptx import Presentation
from pptx.oxml.ns import qn

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
TITLE_TYPES = ("TITLE", "CENTER_TITLE", "VERTICAL_TITLE")
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def patch_theme(pptx_path: str, title_font: str, body_font: str) -> dict:
    """直接改 zip 里的 theme1.xml，设置主题东亚/西文字体。"""
    theme_major = {"ea": title_font, "latin": body_font}
    theme_minor = {"ea": body_font, "latin": body_font}
    patched = {"major": False, "minor": False}
    tmp = pptx_path + ".tmp_fonts"
    with zipfile.ZipFile(pptx_path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "ppt/theme/theme1.xml":
                text = data.decode("utf-8")
                text = _patch_theme_xml(text, "majorFont", theme_major, patched, "major")
                text = _patch_theme_xml(text, "minorFont", theme_minor, patched, "minor")
                data = text.encode("utf-8")
            zout.writestr(item, data)
    import os
    import time
    for attempt in range(5):  # Windows 下目标文件可能被杀软/句柄短暂锁定
        try:
            os.replace(tmp, pptx_path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5)
    return patched


def _patch_theme_xml(text: str, font_scheme: str, fonts: dict, patched: dict, key: str) -> str:
    m = re.search(rf"<a:{font_scheme}>(.*?)</a:{font_scheme}>", text, re.S)
    if not m:
        return text
    block = m.group(1)
    for slot in ("latin", "ea"):
        target = fonts[slot]
        if f"<a:{slot} " in block:
            block = re.sub(rf'<a:{slot} typeface="[^"]*"',
                           f'<a:{slot} typeface="{target}"', block, count=1)
        else:  # 缺槽位时补在 fontScheme 开头（schema 允许的顺序内）
            block = f'<a:{slot} typeface="{target}"/>' + block
        patched[key] = True
    return text[:m.start(1)] + block + text[m.end(1):]


def fix_runs(pptx_path: str, title_font: str, body_font: str) -> dict:
    prs = Presentation(pptx_path)
    stats = {"slides": len(prs.slides), "runs_cjk": 0, "runs_fixed": 0, "title_runs": 0}

    def set_fonts(run, font: str, latin: str) -> None:
        run.font.name = latin  # latin 槽位
        rpr = run._r.get_or_add_rPr()
        ea = rpr.find(qn("a:ea"))
        if ea is None:
            ea = rpr.makeelement(qn("a:ea"), {})
            latin_el = rpr.find(qn("a:latin"))
            if latin_el is not None:
                latin_el.addnext(ea)
            else:
                rpr.append(ea)
        ea.set("typeface", font)

    def walk(shapes):
        for shape in shapes:
            if shape.shape_type == 6:  # GROUP
                walk(shape.shapes)
                continue
            if not getattr(shape, "has_text_frame", False):
                continue
            is_title = False
            try:
                if shape.is_placeholder:
                    is_title = str(shape.placeholder_format.type).upper().startswith(TITLE_TYPES) \
                        or any(str(shape.placeholder_format.type).upper() == t for t in TITLE_TYPES)
            except Exception:
                pass
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if not run.text or not CJK_RE.search(run.text):
                        continue
                    stats["runs_cjk"] += 1
                    font = title_font if is_title else body_font
                    set_fonts(run, font, body_font)
                    stats["runs_fixed"] += 1
                    if is_title:
                        stats["title_runs"] += 1

    for slide in prs.slides:
        walk(slide.shapes)
    prs.save(pptx_path)
    return stats


def fit_pictures(pptx_path: str, max_slide_chars: int = 0) -> dict:
    """把「纯图页」（除标题外无正文的幻灯片）的图片放大铺满内容区并居中。

    pandoc 按 4:3 时代的版式占位符（约 9x3.7in）放置图片，16:9 画布上显得小且
    偏左。对含正文的页不动（避免与文字重叠），只处理标题+图片的整图页。
    """
    from pptx import Presentation as _P
    from pptx.util import Inches as _In

    prs = _P(pptx_path)
    box_l, box_t = 0.45, 1.30          # 内容区（标题以下）
    box_w, box_h = 12.43, 5.85
    fitted = 0
    for slide in prs.slides:
        pics = [sh for sh in slide.shapes if sh.shape_type == 13]
        others = [sh for sh in slide.shapes
                  if sh.shape_type != 13 and getattr(sh, "has_text_frame", False)
                  and sh.text_frame.text.strip()
                  and not (sh.is_placeholder and "TITLE" in str(sh.placeholder_format.type).upper())]
        if len(pics) != 1 or others:
            continue  # 只处理"单图整页"
        pic = pics[0]
        aspect = pic.height / pic.width if pic.width else 1.0
        w = box_w
        h = w * aspect
        if h > box_h:
            h = box_h
            w = h / aspect
        pic.left, pic.top = _In(box_l), _In(box_t + (box_h - h) / 2)
        pic.width, pic.height = _In(w), _In(h)
        fitted += 1
    prs.save(pptx_path)
    return {"pictures_fitted": fitted}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pptx")
    parser.add_argument("--title-font", default="黑体")
    parser.add_argument("--body-font", default="微软雅黑")
    ns = parser.parse_args()

    result: dict = {"file": ns.pptx, "ok": True}
    try:
        result["theme"] = patch_theme(ns.pptx, ns.title_font, ns.body_font)
        result["runs"] = fix_runs(ns.pptx, ns.title_font, ns.body_font)
        result["fit"] = fit_pictures(ns.pptx)
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
