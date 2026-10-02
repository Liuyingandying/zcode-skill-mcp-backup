# -*- coding: utf-8 -*-
"""paper-pipeline-fixer 机械管线: assemble(装配+修复) / check(六项质量门) / compile(两遍编译+日志解析)
全部逻辑固化 run_001 论文链路的实证失败。标准库实现。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


# ---------- assemble ----------
def cmd_assemble(a):
    tpl = Path(a.template).read_text(encoding="utf-8").splitlines()
    pre = []
    for ln in tpl:
        if ln.strip().startswith("\\begin{document}") and not ln.lstrip().startswith("%"):
            break
        pre.append(ln)
    pre = "\n".join(pre)
    adds = []
    if "\\usepackage{graphicx}" not in pre:
        pre = re.sub(r"(\\documentclass[^\n]+\n)", r"\1\\usepackage{graphicx}\n", pre, count=1)
        adds.append("graphicx added")
    if a.figures_dir and "\\graphicspath" not in pre:
        gp = "\\graphicspath{{" + Path(a.figures_dir).as_posix() + "/}}"
        pre += "\n" + gp
        adds.append("graphicspath added")
    body = Path(a.body).read_text(encoding="utf-8")
    for token in ("\\begin{document}", "\\end{document}"):
        if token in body:
            print(f"[assemble][FAIL] body 不应包含 {token}（body 是内文，不是完整文档）")
            sys.exit(2)
    fixed = 0
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.endswith("\\") and not ln.endswith("\\\\"):
            lines[i] = ln + "\\"
            fixed += 1
    missing = [m for m in re.findall(r"\\(?:input|include)\{([^}]+)\}", body)
               if not (Path(a.out).parent / (m if m.endswith(".tex") else m + ".tex")).exists()]
    out = pre + "\n\\begin{document}\n" + "\n".join(lines) + "\n\\end{document}\n"
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"[assemble] OK -> {a.out} | 行尾修复{fixed} | {'; '.join(adds) or '无附加'} | "
          f"body缺失\\input目标: {missing or '无'}")


# ---------- check ----------
GATE_FIG, GATE_NUM, GATE_TAB, GATE_PH, GATE_TPL, GATE_DOC = \
    "figures", "numeric_provenance", "table_rows", "placeholders", "template_leftover", "document_shape"


def cmd_check(a):
    paper = Path(a.paper).read_text(encoding="utf-8")
    fails, warns = [], []
    body = paper.split("\\begin{document}", 1)[-1] if "\\begin{document}" in paper else paper
    body_nc = "\n".join("" if ln.lstrip().startswith("%") else ln for ln in body.split("\n"))

    # G1 图片存在
    figs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body_nc)
    fdir = Path(a.figures_dir) if a.figures_dir else None
    miss = [f for f in figs if fdir and not (fdir / Path(f).name).exists()]
    if miss:
        fails.append((GATE_FIG, miss))
    fig_missing = miss

    # G2 数值溯源
    scan = re.sub(r"(?:width|height|scale)=\d*\.?\d+(?:\\textwidth|\\linewidth)?", "", body_nc)
    results_text = ""
    rdir = Path(a.results_dir)
    for p in sorted(rdir.rglob("*")):
        if p.suffix.lower() in (".md", ".csv", ".json", ".txt", ".tex") and p.is_file():
            results_text += p.read_text(encoding="utf-8", errors="ignore")
    provenance_fail = []
    for n in re.findall(r"(?<![\d.])(\d+\.\d+)(?![\d])", scan):
        if n in results_text:
            continue
        v = float(n)
        for conv in (v * 100, v / 100):
            if f"{conv:g}" in results_text:
                break
        else:
            provenance_fail.append(n)
    if provenance_fail:
        fails.append(("numeric_provenance", provenance_fail))

    # G3 表格换行
    bad_rows = []
    in_tab = False
    for i, ln in enumerate(body.split("\n")):
        if "\\begin{tabular" in ln:
            in_tab = True
        elif "\\end{tabular" in ln:
            in_tab = False
        elif in_tab and ln.endswith("\\") and not ln.endswith("\\\\"):
            bad_rows.append(i + 1)
    if bad_rows:
        fails.append(("table_rows", f"行尾单反斜杠@行{bad_rows}"))

    # G4 占位符
    ph = re.findall(r"TODO|FIXME|XXX|占位|待补|\?\?\?", body_nc)
    if ph:
        fails.append(("placeholders", ph[:8]))

    # G5 模板残留
    if paper.count("\\begin{document}") != 1:
        fails.append(("template_leftover", f"begin{{document}}×{paper.count(chr(92)+'begin{document}')}"))
    for m in re.findall(r"\\(?:input|include)\{([^}]+)\}", body_nc):
        fails.append(("template_leftover", f"正文\\input未解析: {m}"))
    # G5 模板残留（先剥离 LaTeX 命令序列, 避免 \: 等间距命令被误判为盘符路径）
    leak_scan = re.sub(r"\\[a-zA-Z]+|\\[,;:! ]", "", body_nc)
    leaks = re.findall(r"[A-Za-z]:\\[\w\\ ]+|/c/Users", leak_scan)
    if leaks:
        fails.append(("template_leftover", f"路径泄露: {leaks[:4]}"))
    if fig_missing:
        warns.append(f"figures缺失: {fig_missing}")

    report = {
        "paper": str(a.paper), "ok": not fails,
        "gates": {
            GATE_FIG: {"checked": len(figs), "missing": fig_missing},
            GATE_NUM: {"checked_decimals": len(re.findall(r"(?<![\d.])(\d+\.\d+)(?![\d])", scan)),
                       "untraced": provenance_fail},
            GATE_TAB: {"bad_rows": bad_rows},
            GATE_PH: {"hits": ph},
            GATE_TPL: {"leaks": leaks},
            GATE_DOC: {"begin_document_count": paper.count("\\begin{document}")},
        },
        "fails": [list(f) if isinstance(f, tuple) else f for f in fails],
        "warnings": warns,
    }
    out = Path(a.out) if a.out else Path(str(a.paper) + ".check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[check] {'ALL PASS' if report['ok'] else 'FAIL %d项' % len(fails)} -> {out}")
    sys.exit(0 if report["ok"] else 1)


# ---------- compile ----------
def find_engine(engine):
    p = shutil.which(engine)
    if p:
        return p
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MiKTeX/miktex/bin/x64" / (engine + ".exe")
    return str(cand) if cand.exists() else None


def cmd_compile(a):
    eng = find_engine(a.engine)
    if not eng:
        print(f"[compile][FAIL] 找不到 {a.engine}")
        sys.exit(2)
    wd = Path(a.paper).parent
    codes = []
    for _ in range(2):
        r = subprocess.run([eng, "-interaction=nonstopmode", "-halt-on-error", Path(a.paper).name],
                           cwd=wd, capture_output=True, text=True)
        codes.append(r.returncode)
    logf = wd / (Path(a.paper).stem + ".log")
    log = logf.read_text(encoding="utf-8", errors="ignore") if logf.exists() else ""
    errors = len(re.findall(r"^!", log, re.M))
    m = re.search(r"Output written on .+? \((\d+) pages", log)
    pages = m.group(1) if m else "?"
    rep = {"engine": eng, "pass_exits": codes, "errors": errors, "pages": pages,
           "ok": codes == [0, 0] and errors == 0}
    print(json.dumps(rep, ensure_ascii=False))
    sys.exit(0 if rep["ok"] else 1)


def main():
    ap = argparse.ArgumentParser(description="paper-pipeline-fixer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("assemble")
    p.add_argument("--template", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--figures-dir")
    p.set_defaults(fn=cmd_assemble)

    p = sub.add_parser("check")
    p.add_argument("--paper", required=True)
    p.add_argument("--results-dir", required=True)
    p.add_argument("--figures-dir")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("compile")
    p.add_argument("--paper", required=True)
    p.add_argument("--engine", default="xelatex")
    p.set_defaults(fn=cmd_compile)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
