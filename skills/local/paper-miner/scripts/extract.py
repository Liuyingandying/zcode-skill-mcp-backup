# -*- coding: utf-8 -*-
"""extract.py —— PDF -> 文本缓存 (PyMuPDF)。文本量<2000字符判扫描件(needs_ocr)。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")


def extract_text(pdf_path: str, max_pages: int = 12) -> dict:
    """提取前 max_pages 页文本(摘要/目录/模型集中在前的页), 返回 {text, pages, chars}"""
    doc = pymupdf.open(pdf_path)
    pages = min(doc.page_count, max_pages)
    chunks = []
    for i in range(pages):
        chunks.append(doc[i].get_text("text"))
    doc.close()
    text = "\n".join(chunks)
    return {"text": text, "pages": pages, "chars": len(text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--ids", required=True, help="逗号分隔的论文 id")
    ap.add_argument("--cache-dir", default=str(Path(__file__).parent / "cache"))
    ap.add_argument("--max-pages", type=int, default=12)
    a = ap.parse_args()
    inv = json.loads(Path(a.inventory).read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in inv["papers"]}
    cache = Path(a.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    results = {}
    for pid in [x.strip() for x in a.ids.split(",")]:
        p = by_id.get(pid)
        if not p:
            print(f"[extract][FAIL] inventory 无 {pid}")
            continue
        try:
            r = extract_text(p["file"], a.max_pages)
        except Exception as e:  # noqa: BLE001
            print(f"[extract][FAIL] {pid}: {e}")
            continue
        r["needs_ocr"] = r["chars"] < 2000
        (cache / f"{pid}.txt").write_text(r["text"], encoding="utf-8")
        results[pid] = {"pages": r["pages"], "chars": r["chars"], "needs_ocr": r["needs_ocr"]}
        print(f"[extract] {pid}: {r['pages']}p {r['chars']}ch {'⚠扫描件' if r['needs_ocr'] else 'OK'}")
    (cache / "extract_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
