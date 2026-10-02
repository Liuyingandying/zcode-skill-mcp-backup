#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收：完成判定 + 产物核对。不得把 pending==0 当 completed。

判定规则：
  COMPLETED               = done+recovered == target 且 failed==0 且 claimed==0 且 pending==0
  COMPLETED_WITH_FAILURES = 全终态、有失败、成功率 >= 50%
  FAILED_WITH_RESULTS     = 全终态、有失败、成功率 <  50%
产物核对：每个 done/recovered 单元必须 metadata.json 自洽 + content.md 非空 +
work_id 以 work_ 开头且全局唯一（key_2001 验证口径）。

用法：
  python validate_outputs.py --plan night_20260927 [--json] [--report]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (artifact_ok, atomic_write_text, find_node_root,  # noqa: E402
                        judge_counts, load_registry, read_state_counts,
                        reconfigure_stdio, reports_dir, run_dir_for, success_count)

FINAL = ("COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS")


def validate_line(node, line: dict) -> dict:
    out = {"line_id": line["line_id"], "tag": line["tag"], "target": line["target"],
           "done": 0, "failed": 0, "recovered_success": 0, "claimed": 0,
           "pending": 0, "artifact_ok": 0, "artifact_missing": [],
           "dup_work_ids": [], "size_mismatch": None, "status": "NO_STATE"}
    state, counts = read_state_counts(node, line["tag"])
    if state is None:
        return out
    units = state.get("units", [])
    out["size_mismatch"] = (len(units) != line["target"]) or \
                           (state.get("size") != line["target"])
    out.update({k: counts.get(k, 0) for k in
                ("done", "failed", "recovered_success", "claimed", "pending")})
    out["status"] = judge_counts(counts, line["target"])

    rd = run_dir_for(node, line["tag"])
    work_ids = {}
    for u in units:
        if u.get("status") not in ("done", "recovered_success"):
            continue
        uid = u.get("unit_id", "")
        if artifact_ok(rd, uid):
            out["artifact_ok"] += 1
        else:
            out["artifact_missing"].append(uid)
        wid = u.get("work_id")
        if wid:
            work_ids.setdefault(wid, []).append(uid)
    out["dup_work_ids"] = [f"{wid}x{len(v)}" for wid, v in work_ids.items() if len(v) > 1]
    return out


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="NightPlan 产出验收")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true", help="写验收报告到 reports/")
    args = ap.parse_args()

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[validate] 未找到计划：{args.plan}")
        return 2
    node, msg = find_node_root()
    if node is None:
        print(f"[validate] {msg}")
        return 2

    results = [validate_line(node, line) for _, line in sorted(plan["lines"].items())]

    overall_ok = True
    problems = []
    for r in results:
        if r["status"] not in FINAL:
            overall_ok = False
            problems.append(f"{r['line_id']}: 非终态 {r['status']}")
        if r["artifact_missing"]:
            overall_ok = False
            problems.append(f"{r['line_id']}: {len(r['artifact_missing'])} 个成功单元"
                            f"缺产物（例：{r['artifact_missing'][:3]}）")
        if r["dup_work_ids"]:
            overall_ok = False
            problems.append(f"{r['line_id']}: work_id 重复 {r['dup_work_ids'][:5]}")
        if r["size_mismatch"]:
            problems.append(f"{r['line_id']}: state 单元数与 target 不一致（需人工核对）")

    total_target = sum(r["target"] for r in results)
    total_done = sum(success_count(r) for r in results)
    total_failed = sum(r["failed"] for r in results)

    if args.json:
        print(json.dumps({"plan_id": args.plan, "overall_ok": overall_ok,
                          "total": {"target": total_target, "success": total_done,
                                    "failed": total_failed},
                          "lines": results, "problems": problems},
                         ensure_ascii=False, indent=2))
    else:
        print(f"[validate] {args.plan}：成功 {total_done}/{total_target}，"
              f"失败 {total_failed}，overall_ok={overall_ok}")
        for r in results:
            print(f"  {r['line_id']:<14} {r['status']:<24} done={r['done']} "
                  f"failed={r['failed']} recovered={r['recovered_success']} "
                  f"artifact_ok={r['artifact_ok']}"
                  + (f" MISSING={len(r['artifact_missing'])}" if r["artifact_missing"] else ""))
        for p in problems:
            print(f"  ! {p}")
        for r in results:
            if r["status"] in FINAL:
                print(f"  hint: python production_node/node_check.py verify-run "
                      f"--tag {r['tag']} --expect-done {success_count(r)} "
                      f"--expect-total {r['target']}")

    if args.report:
        md = [f"# VALIDATION REPORT — {args.plan}", "",
              f"- overall_ok: {overall_ok}", f"- 成功 {total_done}/{total_target}，"
              f"失败 {total_failed}", ""]
        md += ["| LINE | STATUS | DONE | FAILED | RECOVERED | ARTIFACT_OK | MISSING |",
               "|---|---|---|---|---|---|---|"]
        for r in results:
            md.append(f"| {r['line_id']} | {r['status']} | {r['done']} | {r['failed']} | "
                      f"{r['recovered_success']} | {r['artifact_ok']} | "
                      f"{len(r['artifact_missing'])} |")
        md += [""] + [f"- ! {p}" for p in problems]
        path = reports_dir() / f"validate_{args.plan}.md"
        atomic_write_text(path, "\n".join(md) + "\n")
        print(f"[validate] 报告已写：{path}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
