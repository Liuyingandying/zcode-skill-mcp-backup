# -*- coding: utf-8 -*-
"""optimization_review —— 优化类结果专项审查（modeling-reviewer 增强，run_003 起生效）
检查五个维度：目标函数定义 / 变量可观测性 / 约束完整性 / 边界条件 / 优化结果验证。
前四项以 spec 声明+人工判读结合；第五项（结果验证）支持自动执行校验脚本与阈值断言。

用法: python optimization_review.py --spec opt_review_spec.json --out opt_review_section.md
spec 结构:
{
  "subject": "...",
  "objective_definition": [{"name":..., "given_by_problem": true/false, "description":..., "sanity_check":...}],
  "observability":        [{"name":..., "observable": "...", "unobservable": "...", "impact":...}],
  "constraints":          [{"name":..., "declared": "...", "enforced_in_code": true/false, "evidence":...}],
  "boundary_conditions":  [{"name":..., "condition": "...", "behavior": "...", "handled": true/false}],
  "auto_checks":   [ review.py 兼容的 json_scalar/boundary/monotonicity 检查 (在 results_dir 下执行) ],
  "verify_scripts": [{"name":..., "script": "path", "cwd": "path"}]   # exit!=0 即 FAIL
}
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    results = Path(args.results_dir)

    # 自动检查: 复用 review.py 的执行器
    here = Path(__file__).parent
    auto_lines = []
    if spec.get("auto_checks"):
        tmp = results.parent / "_opt_auto_checks.json"
        tmp.write_text(json.dumps(
            {"subject": spec.get("subject", ""), "json_checks": spec["auto_checks"]},
            ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(here / "review.py"), "--spec", str(tmp),
                            "--results-root", str(results), "--out", str(tmp.with_suffix(".md"))],
                           capture_output=True, text=True)
        auto_lines.append(r.stdout.strip())
        try:
            md = tmp.with_suffix(".md").read_text(encoding="utf-8")
            table = md.split("## 自动探针结果")[-1].split("##")[0].strip()
            auto_lines.append(table)
        except Exception as e:  # noqa: BLE001
            auto_lines.append(f"自动检查解析失败: {e}")

    # 校验脚本
    script_lines = []
    for vs in spec.get("verify_scripts", []):
        r = subprocess.run([sys.executable, vs["script"]], cwd=vs.get("cwd") or ".", capture_output=True, text=True)
        script_lines.append(f"- {'PASS' if r.returncode == 0 else 'FAIL'} {vs['name']} (exit={r.returncode}) {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''}")

    lines = [f"## optimization_review —— {spec.get('subject', '')}",
             f"生成: {datetime.now().strftime('%F %T')}", ""]
    for key, title in [("objective_definition", "1. 目标函数定义"),
                       ("observability", "2. 变量可观测性"),
                       ("constraints", "3. 约束完整性"),
                       ("boundary_conditions", "4. 边界条件")]:
        lines.append(f"### {title}")
        items = spec.get(key, [])
        if not items:
            lines.append("-（无声明项）")
        for it in items:
            flag = "" if it.get("enforced_in_code", it.get("handled", it.get("given_by_problem", True))) \
                else " ⚠需人工复核"
            lines.append(f"- **{it.get('name', '')}**{flag}：{it.get('description', it.get('observable', it.get('declared', it.get('condition', ''))))}"
                         + (f"｜evidence: {it['evidence']}" if it.get("evidence") else ""))
        lines.append("")
    lines.append("### 5. 优化结果验证（自动）")
    lines += auto_lines or ["-（无自动检查）"]
    if script_lines:
        lines.append("")
        lines.append("校验脚本：")
        lines += script_lines
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"[opt_review] section -> {args.out} | verify_scripts {len(spec.get('verify_scripts', []))} | "
          f"auto_checks {len(spec.get('auto_checks', []))}")


if __name__ == "__main__":
    main()
