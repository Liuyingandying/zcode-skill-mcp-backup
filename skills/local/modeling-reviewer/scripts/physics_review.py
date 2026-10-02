# -*- coding: utf-8 -*-
"""physics_review —— 机理类问题专项审查（modeling-reviewer 增强，run_004 起生效）
五维度：方程量纲一致性 / 初始边界条件完整性 / 参数来源可追溯 / 黑箱替代检查 / 数值求解稳定性。
自动项在 results_dir 与 exp_dir 内机器核验；声明项由 spec 提供并标记人工复核状态。

用法: python physics_review.py --spec physics_review_spec.json --results-dir DIR --exp-dir DIR --out section.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--exp-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    results, exp = Path(args.results_dir), Path(args.exp_dir)

    exp_src = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                        for p in sorted(exp.glob("*.py")))

    lines = [f"## physics_review —— {spec.get('subject', '')}",
             f"生成: {datetime.now().strftime('%F %T')}", ""]

    # 1) 量纲一致性: spec 声明方程的量纲 + 关键换算在代码中存在
    lines.append("### 1. 方程量纲一致性")
    for d in spec.get("dimensions", []):
        ok = d["lhs"] == d["rhs"]
        lines.append(f"- {'PASS' if ok else 'FAIL'} {d['name']}: [{d['lhs']}] = [{d['rhs']}]"
                     + ("" if ok else " ⚠量纲不匹配"))
    for conv in spec.get("unit_conversions_in_code", []):
        found = bool(re.search(conv["pattern"], exp_src))
        lines.append(f"- {'PASS' if found else 'FAIL'} 代码含换算/单位声明: {conv['name']}"
                     + (f"（pattern `{conv['pattern']}`）" if not found else ""))
    lines.append("")

    # 2) 初始/边界条件: 声明 + 代码存在性
    lines.append("### 2. 初始/边界条件完整性")
    for c in spec.get("initial_boundary", []):
        found = bool(re.search(c["code_pattern"], exp_src))
        lines.append(f"- {'PASS' if found else 'FLAG'} {c['name']}: {c['value']}"
                     + ("" if found else "（未在代码中定位到，需人工复核）"))
    lines.append("")

    # 3) 参数来源可追溯
    lines.append("### 3. 参数来源可追溯")
    for p in spec.get("parameters", []):
        src = p["source"]
        ok = True
        detail = ""
        if src == "identified":
            try:
                ident = json.loads((results / p["ident_report"]).read_text(encoding="utf-8"))
                val = float(ident[p["key"]])
                ok = abs(val - p["expected"]) <= p["tolerance"]
                detail = f"辨识值={val}, 基准={p['expected']}±{p['tolerance']}"
            except Exception as e:  # noqa: BLE001
                ok, detail = False, f"辨识报告读取失败: {e}"
        lines.append(f"- {'PASS' if ok else 'FAIL'} {p['name']}（来源: {src}）{detail}")
    lines.append("")

    # 4) 黑箱替代检查
    lines.append("### 4. 机理模型 vs 黑箱替代")
    ml_hits = sorted({m for pat in spec.get("blackbox_patterns", [])
                      for m in re.findall(pat, exp_src)})
    lines.append(f"- {'FLAG' if ml_hits else 'PASS'} 实验代码机器学习库引用: {ml_hits or '无'}")
    for m in spec.get("mechanism_evidence", []):
        found = bool(re.search(m["code_pattern"], exp_src))
        lines.append(f"- {'PASS' if found else 'FAIL'} 机理要素在代码中落地: {m['name']}"
                     + (f"（{m['code_pattern']}）" if not found else ""))
    lines.append("")

    # 5) 数值求解稳定性
    lines.append("### 5. 数值求解稳定性")
    try:
        stab = json.loads((results / spec["stability_report"]).read_text(encoding="utf-8"))
        obj = stab
        for key in spec["stability_metric_key"].split("."):
            obj = obj[key]
        ratio = float(obj)
        thr = float(spec["stability_threshold"])
        lines.append(f"- {'PASS' if ratio <= thr else 'FLAG'} 步长减半输出相对变化 "
                     f"= {ratio:.2e} (阈值 {thr:.0e})")
    except Exception as e:  # noqa: BLE001
        lines.append(f"- FAIL 稳定性报告缺失或格式错误: {e}")
    lines.append("")

    lines.append("> 声明项由生成阶段填写、审查阶段复核；auto 项由本脚本机器核验。")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    n_fail = sum(1 for ln in lines if "FAIL" in ln)
    print(f"[physics_review] section -> {args.out} | FAIL {n_fail}")


if __name__ == "__main__":
    main()
