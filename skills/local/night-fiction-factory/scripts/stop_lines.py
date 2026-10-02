#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全停止生产线：只停本 NightPlan 自己拥有、且能对上 tag/run_dir 的进程树。

绝对禁止：
  taskkill /IM python.exe           —— 会杀掉 ZCode/Dashboard/Gateway/其他 Python
  杀任何注册簿里没有、或命令行与 tag 不匹配的 PID（防 PID 复用误杀）

用法：
  python stop_lines.py --plan night_20260927 [--line scifi_01] [--reason "今晚先停"]
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (audit_log, build_stop_plan, find_node_root, iso_now,  # noqa: E402
                        kill_tree, list_python_processes, load_registry,
                        match_line_pids, read_state_counts, reconfigure_stdio,
                        run_dir_for, save_registry)

FINAL = ("COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS")


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="安全停止生产线（PID 隔离）")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--line", default=None, help="只停该 line_id（其余继续）")
    ap.add_argument("--reason", default="manual stop")
    args = ap.parse_args()

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[stop] 未找到计划：{args.plan}")
        return 2
    node, msg = find_node_root()
    if node is None:
        print(f"[stop] {msg}")
        return 2
    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"[stop] 无法获取进程表，拒绝盲杀：{e}")
        return 2

    only = [args.line] if args.line else None
    plan_stops = build_stop_plan(plan, only, procs)

    if not plan_stops["kills"]:
        print("[stop] 没有需要停止的存活进程：")
        for s in plan_stops["skipped"]:
            print(f"  - {s['line_id']}: {s['reason']}")
        return 0

    killed = []
    for k in plan_stops["kills"]:
        for pid in k["pids"]:
            ok = kill_tree(pid, source="night_stop_lines.stop", tag=k["tag"],
                           reason=args.reason, node_root=node)
            print(f"[stop] {k['line_id']}（tag={k['tag']}）kill_tree pid={pid} "
                  f"→ {'OK' if ok else 'FAIL'}")
            if ok:
                killed.append((k["line_id"], pid))

    # 孤儿 worker 二次收割：仍按本计划各线的 run_dir 严格圈定，绝不扫全局
    time.sleep(3.0)
    try:
        procs2 = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        procs2 = []
    for lid, line in sorted(plan["lines"].items()):
        if only and lid not in only:
            continue
        leftovers = match_line_pids(procs2, line["tag"], run_dir_for(node, line["tag"]))
        for pid in leftovers:
            ok = kill_tree(pid, source="night_stop_lines.stop", tag=line["tag"],
                           reason="orphan_cleanup", node_root=node)
            print(f"[stop] {lid} 孤儿 worker 收割 pid={pid} → {'OK' if ok else 'FAIL'}")

    now = iso_now()
    for lid, line in sorted(plan["lines"].items()):
        if only and lid not in only:
            continue
        if line.get("status") in FINAL:
            continue
        if node is not None:
            _, counts = read_state_counts(node, line["tag"])
            if counts:
                line.update(done=counts.get("done", 0), failed=counts.get("failed", 0),
                            pending=counts.get("pending", 0),
                            claimed=counts.get("claimed", 0),
                            recovered_success=counts.get("recovered_success", 0))
        if any(lid == k["line_id"] for k in plan_stops["kills"]):
            line.update(status="STOPPED", pid=None, paused_reason=args.reason,
                        last_activity=now)
            audit_log(f"LINE_STOPPED plan={args.plan} line={lid} tag={line['tag']} "
                      f"reason={args.reason}")
    save_registry(reg)

    print(f"[stop] 完成：停止 {len(killed)} 个进程。已停止线的 state/works 原样保留，"
          f"之后可用 resume_lines.py 同 tag 续跑。")
    for s in plan_stops["skipped"]:
        print(f"  - {s['line_id']}: {s['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
