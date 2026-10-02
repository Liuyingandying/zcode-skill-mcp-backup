#!/usr/bin/env python3
"""docx → pdf，保持 docx 版式与中文字体。

转换链自动降级：MS Word COM → WPS 文字 COM (Kwps) → LibreOffice soffice headless。
本机（Windows + 已装 MS Word/WPS）前两级可用；转换前先更新域，保证目录页码正确，
且不回写 docx（源文件保持原样，updateFields 设置仍在，用户打开 Word/WPS 会自行刷新）。

用法:
    python convert_pdf.py 报告.docx                 # 输出 报告.pdf 到同目录
    python convert_pdf.py 报告.docx -o D:/out       # 指定输出目录

输出 JSON: {"ok":..., "method": "word_com|wps_com|soffice", "pdf":..., "pages": N}；失败退出码 1。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

PDF_FORMAT = 17  # wdExportFormatPDF / WPS 同义


def _com_convert(prog_id: str, docx_abs: str, pdf_abs: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx(prog_id)
    doc = None
    try:
        app.Visible = False
        try:
            app.DisplayAlerts = 0
        except Exception:
            pass
        doc = app.Documents.Open(docx_abs)
        try:  # 刷新域（目录/题注页码），失败不阻塞导出
            doc.Fields.Update()
            for i in range(1, doc.TablesOfContents.Count + 1):
                doc.TablesOfContents(i).Update()
        except Exception:
            pass
        doc.ExportAsFixedFormat(pdf_abs, PDF_FORMAT)
    finally:
        try:
            if doc is not None:
                doc.Close(0)  # 不保存，保持 docx 原样
        except Exception:
            pass
        try:
            app.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


def _soffice_cmd() -> str | None:
    found = shutil.which("soffice")
    if found:
        return found
    for path in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ):
        if os.path.isfile(path):
            return path
    return None


def convert(docx_path: str, out_dir: str | None) -> dict:
    docx_abs = os.path.abspath(docx_path)
    if not os.path.isfile(docx_abs):
        return {"ok": False, "error": f"找不到 {docx_abs}"}
    out_dir_abs = os.path.abspath(out_dir) if out_dir else os.path.dirname(docx_abs)
    os.makedirs(out_dir_abs, exist_ok=True)
    pdf_abs = os.path.join(out_dir_abs, os.path.splitext(os.path.basename(docx_abs))[0] + ".pdf")
    if os.path.abspath(pdf_abs) == docx_abs:
        return {"ok": False, "error": "输出路径与输入相同"}

    attempts: list[dict] = []
    for method, prog_id in (("word_com", "Word.Application"), ("wps_com", "Kwps.Application")):
        try:
            t0 = time.time()
            _com_convert(prog_id, docx_abs, pdf_abs)
            if os.path.isfile(pdf_abs) and os.path.getsize(pdf_abs) > 0:
                attempts.append({"method": method, "seconds": round(time.time() - t0, 1)})
                return _finish(pdf_abs, method)
        except Exception as exc:
            attempts.append({"method": method, "error": f"{type(exc).__name__}: {exc}"})

    soffice = _soffice_cmd()
    if soffice:
        try:
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir_abs, docx_abs],
                           check=True, timeout=180,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if os.path.isfile(pdf_abs) and os.path.getsize(pdf_abs) > 0:
                attempts.append({"method": "soffice"})
                return _finish(pdf_abs, "soffice")
        except Exception as exc:
            attempts.append({"method": "soffice", "error": f"{type(exc).__name__}: {exc}"})
    else:
        attempts.append({"method": "soffice", "error": "未安装 LibreOffice"})

    return {"ok": False, "error": "全部转换途径失败", "attempts": attempts}


def _finish(pdf_abs: str, method: str) -> dict:
    pages = None
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(pdf_abs).pages)
    except Exception:
        pass
    return {"ok": True, "method": method, "pdf": pdf_abs, "pages": pages}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docx")
    parser.add_argument("-o", "--out-dir", default=None)
    ns = parser.parse_args()
    result = convert(ns.docx, ns.out_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
