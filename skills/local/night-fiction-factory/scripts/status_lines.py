#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看 NightPlan 各生产线状态（只读，不写注册簿）。

输出示例：
  Night Plan: night_20260927  (provider=glm, stop_at=08:00)

  LINE          DONE   TOTAL   WORKERS   STATUS
  scifi_01      143    200     2         RUNNING
  mystery_01    200    200     0         COMPLETED

  TOTAL: 343 / 400 (done 340 + recovered 3, failed 0, claimed 0, pending 57)
  Memory: commit 24.1/32.0 GB (75.3%), headroom 7.9 GB
  Network: HEALTHY (tcp 127.0.0.1:8000)

用法：python status_lines.py --plan night_20260927 [--json] [--with-breaker]
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (breaker_from_state, breaker_verdict, effective_line_status,  # noqa: E402
                        evaluate_gate, find_node_root, judge_counts,
                        list_python_processes, load_registry, match_line_pids,
                        probe_provider, query_memory, read_llm_tail,
                        read_state_counts, reconfigure_stdio, resolve_provider,
                        run_dir_for, stale_claimed, success_count)


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="查看生产线状态")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--with-breaker", action="store_true", help="附带各线熔断判定")
    args = ap.parse_args()

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[status] 未找到计划：{args.plan}")
        return 2

    node, _ = find_node_root()
    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        procs = []
    try:
        mem = query_memory()
        gate = evaluate_gate(mem)
        mem_line = (f"commit {mem['commit_used_gb']}/{mem['commit_limit_gb']} GB"
                    f"（{mem['commit_pct']}%，headroom {mem['commit_headroom_gb']} GB），"
                    f"可用物理 {mem['avail_phys_gb']} GB，门禁 {gate['level']}")
    except OSError as e:
        gate, mem_line = None, f"内存查询失败：{e}"

    prof = resolve_provider(plan.get("provider", "glm"))
    net = probe_provider(prof["base_url"])

    rows, totals = [], {"done": 0, "recovered_success": 0, "failed": 0,
                        "claimed": 0, "pending": 0, "target": 0}
    live_workers_total = 0
    detail = []
    mem = None
    for lid, line in sorted(plan["lines"].items()):
        state, counts = (None, None)
        if node is not None:
            state, counts = read_state_counts(node, line["tag"])
        if counts is None:
            eff, done = line.get("status", "PLANNED"), 0
            st = None
            unit_counts = {"pending": line["target"], "claimed": 0, "done": 0,
                           "failed": 0, "recovered_success": 0}
        else:
            unit_counts = counts
            done = success_count(counts)
            judged = judge_counts(counts, line["target"])
            live = match_line_pids(procs, line["tag"], run_dir_for(node, line["tag"]))
            live_workers_total += len(live)
            eff = effective_line_status(line.get("status", "PLANNED"), judged, len(live))
            st = state
        rows.append((lid, done, line["target"], line.get("workers", 0), eff))
        for k in totals:
            totals[k] += unit_counts.get(k, 0) if k != "target" else 0
        totals["target"] += line["target"]
        breaker_note = ""
        if args.with_breaker and node is not None and st is not None:
            recs = read_llm_tail(run_dir_for(node, line["tag"]))
            bv = breaker_verdict(recs) if recs else breaker_from_state(st.get("units", []))
            breaker_note = bv["state"]
            stales = len(stale_claimed(st.get("units", [])))
            if stales:
                breaker_note += f"（stale claimed {stales}）"
        detail.append({"line_id": lid, "status": eff, "done": done,
                       "counts": unit_counts, "breaker": breaker_note or None})

    if args.json:
        print(json.dumps({"plan_id": plan["plan_id"], "stop_at": plan.get("stop_at"),
                          "lines": detail, "totals": totals,
                          "workers_alive": live_workers_total,
                          "memory": mem, "gate": gate["level"] if gate else None,
                          "network": net}, ensure_ascii=False, indent=2))
        return 0

    print(f"Night Plan: {plan['plan_id']}  (provider={plan.get('provider')}, "
          f"stop_at={plan.get('stop_at')})")
    print()
    print(f"{'LINE':<14}{'DONE':>6}{'TOTAL':>8}{'WORKERS':>9}   STATUS")
    for lid, done, target, workers, eff in rows:
        print(f"{lid:<14}{done:>6}{target:>8}{workers:>9}   {eff}"
              + (f"  [{breaker_note}]" if args.with_breaker and breaker_note else ""))
    print()
    print(f"TOTAL: {success_count(totals)} / {totals['target']}  "
          f"(done {totals['done']} + recovered {totals['recovered_success']}, "
          f"failed {totals['failed']}, claimed {totals['claimed']}, "
          f"pending {totals['pending']})")
    print(f"Workers alive: {live_workers_total}")
    print(f"Memory: {mem_line}")
    print(f"Network: tcp={net.get('tcp')} {net.get('host')}:{net.get('port')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
