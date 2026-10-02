# -*- coding: utf-8 -*-
"""modeling-reviewer 自动探针：按 spec 执行方向/单调/边界/小样本检查，输出 RISK_REPORT.md 骨架。
spec 示例见 benchmark/outputs/case01/run_002/review_spec.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

OPS = {"gt": lambda a, b: a > b, "lt": lambda a, b: a < b,
       "ge": lambda a, b: a >= b, "le": lambda a, b: a <= b}


def load(root: Path, spec: dict):
    df = pd.read_csv(root / spec["file"])
    if "match" in spec:
        col, val = next(iter(spec["match"].items()))
        if col == "index":
            df = df[df.iloc[:, 0].astype(str) == str(val)]
        else:
            df = df[df[col].astype(str) == str(val)]
        if len(df) != 1:
            return None, f"行匹配失败({len(df)}条)"
        return df.iloc[0], None
    return df, None


def jpath(obj, path):
    for k in path.split("."):
        obj = obj[k]
    return obj


def run_check(spec: dict, root: Path) -> dict:
    name = spec["name"]
    try:
        kind = spec["type"]
        if kind == "json_scalar":
            obj = json.loads((root / spec["file"]).read_text(encoding="utf-8"))
            val = float(jpath(obj, spec["json_path"]))
            ok = OPS[spec["expect"]["op"]](val, spec["expect"]["value"])
            return {"name": name, "kind": kind, "value": round(val, 4),
                    "expect": spec["expect"], "status": "PASS" if ok else "CRITICAL",
                    "why": spec.get("why", "")}
        row_or_df, err = load(root, spec)
        if err:
            return {"name": name, "kind": "load", "status": "HIGH", "detail": err, "why": spec.get("why", "")}
        if kind == "direction":
            val = float(row_or_df[spec["column"]])
            ok = OPS[spec["expect"]["op"]](val, spec["expect"]["value"])
            return {"name": name, "kind": kind, "value": round(val, 5),
                    "expect": spec["expect"], "status": "PASS" if ok else "CRITICAL",
                    "why": spec.get("why", "")}
        if kind == "monotonicity":
            s = row_or_df.sort_values(spec.get("by", "group"))[spec["column"]]
            ok = s.is_monotonic_increasing if spec["order"] == "increasing" else s.is_monotonic_decreasing
            return {"name": name, "kind": kind, "value": s.tolist(),
                    "expect": spec["order"], "status": "PASS" if ok else "CRITICAL",
                    "why": spec.get("why", "")}
        if kind == "boundary":
            s = row_or_df[spec["column"]] if spec["column"] in row_or_df else row_or_df
            vals = s if hasattr(s, "__iter__") and not isinstance(s, dict) else [s]
            bad = [v for v in vals if not (spec.get("min", -1e18) <= float(v) <= spec.get("max", 1e18))]
            return {"name": name, "kind": kind, "value": list(vals)[:8],
                    "expect": f"[{spec.get('min')},{spec.get('max')}]",
                    "status": "PASS" if not bad else "HIGH", "detail": f"越界{bad}" if bad else "",
                    "why": spec.get("why", "")}
        if kind == "small_sample":
            s = row_or_df[spec["column"]]
            small = s[s < spec["threshold"]]
            return {"name": name, "kind": kind, "value": small.tolist(),
                    "expect": f">={spec['threshold']}",
                    "status": "PASS" if len(small) == 0 else "FLAG",
                    "detail": f"{len(small)}组样本量不足" if len(small) else "",
                    "why": spec.get("why", "")}
        return {"name": name, "status": "HIGH", "detail": f"未知类型 {kind}"}
    except Exception as e:  # noqa: BLE001 —— 审查脚本自身失败也要显性呈现
        return {"name": name, "kind": spec.get("type"), "status": "HIGH",
                "detail": f"探针执行失败: {e}", "why": spec.get("why", "")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--results-root", default=".")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    root = Path(args.results_root)

    results = [run_check(c, root) for c in
               spec.get("direction_checks", []) + spec.get("monotonicity_checks", [])
               + spec.get("boundary_checks", []) + spec.get("small_sample_flags", [])
               + spec.get("json_checks", [])]

    lines = [f"# RISK_REPORT —— {spec.get('subject', '模型审查')}",
             f"生成: {datetime.now().strftime('%F %T')} ｜ 自动探针 {len(results)} 项，"
             f"PASS {sum(r['status'] == 'PASS' for r in results)} / "
             f"非PASS {sum(r['status'] != 'PASS' for r in results)}", "",
             "## 自动探针结果", "",
             "| 级别 | 检查 | 结果 | 预期 | 说明 |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['status']} | {r['name']} | {r.get('value', r.get('detail', ''))} "
                     f"| {r.get('expect', '')} | {r.get('detail', '') or r.get('why', '')} |")
    lines += ["", "## 假设风险（人工，Step1 清单）", "<!-- 待填 -->", "",
              "## 目标函数来源与 sanity check（人工）", "<!-- 待填 -->", "",
              "## 极端情况探针（人工/轻量脚本）", "<!-- 待填 -->", "",
              "## 承诺-兑现对账（人工）", "<!-- 待填 -->", "",
              "## 结论与修复优先级", "<!-- 待填 -->"]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    n_bad = sum(r["status"] != "PASS" for r in results)
    print(f"[review] {len(results)} checks, PASS {len(results)-n_bad}, 非PASS {n_bad} -> {args.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
