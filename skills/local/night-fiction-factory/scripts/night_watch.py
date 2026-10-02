#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夜间守护：采样 + 熔断 + 资源守卫 + 断线自动续跑 + 晨间报告。

每 2~5 分钟一个采样周期（--interval 秒）：
  1. 刷新各线五态计数与进程存活
  2. 网络熔断：某线结尾连续 >= 6 条连接类失败（llm_calls.jsonl，降级用 state）
     → 安全停止该线进程树 → PAUSED_UPSTREAM（state/works 原样保留）
  3. --auto-resume-upstream：熔断线每轮探测网关，连续 2 次通过 → 同 tag 自动续跑
  4. 资源守卫：commit >= 92% 或可用物理 < 1024MB → 只停不启（key_2001 语义）
     最新启动的线先停 → PAUSED_RESOURCE（绝不自动重启，等人工/门禁放行）
  5. 进程全灭但 state 未完成 → FAILED_RESUMABLE（--auto-resume-crash 才自动续跑）
  6. 到 stop_at → 全部安全停止 → 生成 NIGHT_PRODUCTION_REPORT.md

用法：
  python night_watch.py --plan night_20260927 [--interval 240]
                        [--stop-at 08:00] [--auto-resume-upstream]
                        [--auto-resume-crash] [--once] [--max-hours 12]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (audit_log, breaker_from_state, breaker_verdict,  # noqa: E402
                        build_report, build_stop_plan, effective_line_status,
                        evaluate_gate, find_node_root, iso_now, judge_counts,
                        kill_tree, list_python_processes, load_registry,
                        match_line_pids, probe_provider, query_memory, read_llm_tail,
                        read_state_counts, reconfigure_stdio, resolve_provider,
                        run_dir_for, samples_path, save_registry, spawn_detached,
                        stale_claimed, success_count, parse_stop_at, logs_dir,
                        reports_dir, atomic_write_text)

ENGINE_ENTRY = os.path.join("experiments", "multi_worker_generation", "run.py")
FINAL = ("COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS")


def stop_single_line(plan, node, line, reason: str = "night_watch_stop") -> int:
    """只停该线：先杀登记/匹配 PID，再按 run_dir 收割孤儿 worker。"""
    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return 0
    stops = build_stop_plan(plan, [line["line_id"]], procs)
    n = 0
    for k in stops["kills"]:
        for pid in k["pids"]:
            if kill_tree(pid, source="night_watch.stop", tag=line["tag"],
                         reason=reason, node_root=node):
                n += 1
    if n:
        time.sleep(3.0)
        try:
            procs2 = list_python_processes()
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            procs2 = []
        for pid in match_line_pids(procs2, line["tag"], run_dir_for(node, line["tag"])):
            if kill_tree(pid, source="night_watch.stop", tag=line["tag"],
                         reason=reason + ":orphan_cleanup", node_root=node):
                n += 1
    return n


def tick(reg, plan, node, prof, opts, peaks) -> dict:
    """一个采样周期。返回统计。"""
    stats = {"breaker_trips": 0, "gate_stops": 0, "resumes": 0}
    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        procs = []
    try:
        gate = evaluate_gate(query_memory())
        peaks["max_commit_used_gb"] = max(peaks["max_commit_used_gb"],
                                          gate["memory"]["commit_used_gb"])
        peaks["commit_limit_gb"] = gate["memory"]["commit_limit_gb"]
        peaks["min_avail_phys_gb"] = min(peaks["min_avail_phys_gb"],
                                         gate["memory"]["avail_phys_gb"])
    except OSError:
        gate = None

    running_order = sorted((l for l in plan["lines"].values()
                            if l.get("status") == "RUNNING"),
                           key=lambda l: l.get("started_at") or "", reverse=True)

    for lid, line in sorted(plan["lines"].items()):
        if line.get("status") in FINAL:
            continue
        state, counts = read_state_counts(node, line["tag"])
        if counts is None:
            continue
        judged = judge_counts(counts, line["target"])
        rd = run_dir_for(node, line["tag"])
        live = match_line_pids(procs, line["tag"], rd)

        if judged in FINAL:
            line.update(status=judged, pid=None, done=counts.get("done", 0),
                        failed=counts.get("failed", 0), pending=counts.get("pending", 0),
                        claimed=counts.get("claimed", 0),
                        recovered_success=counts.get("recovered_success", 0),
                        last_activity=iso_now())
            continue

        # 熔断判定（只对存活进程的线）
        if live:
            recs = read_llm_tail(rd)
            bv = breaker_verdict(recs) if recs else breaker_from_state(state.get("units", []))
            if bv["state"] == "OUTAGE":
                n = stop_single_line(plan, node, line, "upstream_outage")
                line.update(status="PAUSED_UPSTREAM", pid=None,
                            breach_count=line.get("breach_count", 0) + 1,
                            paused_reason=f"UPSTREAM_OUTAGE: {bv['reason']}",
                            last_activity=iso_now(),
                            notes=(line.get("notes") or [])[-19:] +
                                  [f"{iso_now()} 熔断：{bv['reason']}"])
                audit_log(f"BREAKER_TRIP plan={plan['plan_id']} line={lid} "
                          f"tag={line['tag']} killed={n} evidence={bv['reason'][:120]}")
                stats["breaker_trips"] += 1
                peaks["breaker_trips"] = peaks.get("breaker_trips", 0) + 1
                continue
        else:
            bv = {"state": "UNKNOWN"}

        # 资源守卫：只停不启，最新启动的先停
        if gate and gate["stop_running"] and line["line_id"] in \
                {l["line_id"] for l in running_order[:1]} and live:
            n = stop_single_line(plan, node, line, "resource_guard")
            line.update(status="PAUSED_RESOURCE", pid=None,
                        paused_reason="；".join(gate["reasons"]),
                        last_activity=iso_now())
            audit_log(f"RESOURCE_STOP plan={plan['plan_id']} line={lid} killed={n} "
                      f"commit={gate['memory']['commit_pct']}%")
            peaks["gate_trips"] = peaks.get("gate_trips", 0) + 1
            stats["gate_stops"] += 1
            continue

        # 上游恢复自动续跑
        if (line.get("status") == "PAUSED_UPSTREAM" and not live
                and opts.auto_resume_upstream):
            net = probe_provider(prof["base_url"])
            streak_key = f"_probe_ok_{lid}"
            if net.get("tcp") is True:
                plan[streak_key] = plan.get(streak_key, 0) + 1
            else:
                plan[streak_key] = 0
            if plan.get(streak_key, 0) >= 2:
                if gate is None or gate["allow_new_line"]:
                    pid = spawn_detached(
                        [sys.executable, ENGINE_ENTRY, "--limit", str(line["target"]),
                         "--workers", str(line["workers"]), "--tag", line["tag"], "--resume"],
                        cwd=node, log_path=logs_dir() / f"{line['tag']}.launch.log")
                    line.update(status="RUNNING", pid=pid, started_at=iso_now(),
                                paused_reason=None, last_activity=iso_now(),
                                restarts=line.get("restarts", 0) + 1,
                                notes=(line.get("notes") or [])[-19:] +
                                      [f"{iso_now()} 上游恢复自动续跑"])
                    plan[streak_key] = 0
                    stats["resumes"] += 1
                    audit_log(f"AUTO_RESUME plan={args_plan_id(plan)} line={lid} pid={pid}")

        # 进程全灭但未完成
        eff = effective_line_status(line.get("status", "PLANNED"), judged, len(live))
        if eff == "FAILED_RESUMABLE" and opts.auto_resume_crash:
            if gate is None or gate["allow_new_line"]:
                stales = len(stale_claimed(state.get("units", [])))
                pid = spawn_detached(
                    [sys.executable, ENGINE_ENTRY, "--limit", str(line["target"]),
                     "--workers", str(line["workers"]), "--tag", line["tag"], "--resume"],
                    cwd=node, log_path=logs_dir() / f"{line['tag']}.launch.log")
                line.update(status="RUNNING", pid=pid, started_at=iso_now(),
                            last_activity=iso_now(),
                            restarts=line.get("restarts", 0) + 1)
                stats["resumes"] += 1
                audit_log(f"AUTO_RESUME_CRASH plan={args_plan_id(plan)} line={lid} "
                          f"pid={pid} stale={stales}")
                continue
        line.update(status=eff, pid=(line.get("pid") if live else None),
                    done=counts.get("done", 0), failed=counts.get("failed", 0),
                    pending=counts.get("pending", 0), claimed=counts.get("claimed", 0),
                    recovered_success=counts.get("recovered_success", 0),
                    last_activity=iso_now())

    save_registry(reg)
    return stats


def args_plan_id(plan):
    return plan.get("plan_id", "?")


def write_report(reg, plan, node, peaks, runtime, notes) -> Path:
    line_details = []
    for lid, line in sorted(plan["lines"].items()):
        note = line.get("paused_reason") or ""
        if line.get("restarts"):
            note = f"重启 {line['restarts']} 次；" + note
        line_details.append({"line_id": lid, "tag": line["tag"], "target": line["target"],
                             "done": line.get("done", 0), "failed": line.get("failed", 0),
                             "recovered_success": line.get("recovered_success", 0),
                             "status": line.get("status"), "note": note,
                             "run_dir": line.get("run_dir") or
                                        (str(run_dir_for(node, line["tag"]))
                                         if node else None)})
    md = build_report(plan, line_details, runtime, peaks, notes)
    path = reports_dir() / f"NIGHT_PRODUCTION_REPORT_{plan['plan_id']}.md"
    atomic_write_text(path, md)
    return path


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="夜间守护循环")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--interval", type=int, default=240, help="采样间隔秒（120~300 推荐）")
    ap.add_argument("--stop-at", default=None, help="覆盖计划里的 stop_at（HH:MM）")
    ap.add_argument("--auto-resume-upstream", action="store_true",
                    help="熔断线在网关连续 2 次探测通过后自动续跑")
    ap.add_argument("--auto-resume-crash", action="store_true",
                    help="进程全灭的线自动续跑（默认只标记 FAILED_RESUMABLE）")
    ap.add_argument("--once", action="store_true", help="只跑一个采样周期（调试用）")
    ap.add_argument("--max-hours", type=float, default=14.0, help="硬超时保险丝")
    args = ap.parse_args()

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[watch] 未找到计划：{args.plan}")
        return 2
    node, msg = find_node_root()
    if node is None:
        print(f"[watch] {msg}")
        return 2
    prof = resolve_provider(plan.get("provider", "glm"))
    deadline = parse_stop_at(args.stop_at or plan.get("stop_at") or "08:00")
    hard_deadline = time.time() + args.max_hours * 3600

    peaks = {"max_commit_used_gb": 0.0, "min_avail_phys_gb": 1e9,
             "commit_limit_gb": 0.0, "gate_trips": 0, "breaker_trips": 0}
    started = time.time()
    sp = samples_path(plan["plan_id"])
    sp.parent.mkdir(parents=True, exist_ok=True)
    notes = []
    print(f"[watch] 开始守护 {plan['plan_id']}：interval={args.interval}s "
          f"stop_at={deadline.strftime('%m-%d %H:%M')} "
          f"auto_resume_upstream={args.auto_resume_upstream}")

    while True:
        stats = tick(reg, plan, node, prof, args, peaks)
        ts = iso_now()
        running = [lid for lid, l in plan["lines"].items() if l.get("status") == "RUNNING"]
        done_total = sum(l.get("done", 0) + l.get("recovered_success", 0)
                         for l in plan["lines"].values())
        with open(sp, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": ts, "running": len(running),
                                "done_total": done_total,
                                "commit_used_gb": peaks["max_commit_used_gb"],
                                "stats": stats}, ensure_ascii=False) + "\n")
        print(f"[watch] {ts} running={len(running)} 成功={done_total} stats={stats}")

        finals = all(l.get("status") in FINAL or
                     l.get("status") in ("PLANNED", "STOPPED",
                                         "PAUSED_RESOURCE", "FAILED_RESUMABLE")
                     for l in plan["lines"].values())
        no_live_running = not running
        if finals and no_live_running:
            notes.append("所有线已到终态或无存活进程，守护结束。")
            break
        if args.once:
            notes.append("--once 调试模式：单周期后退出。")
            break
        if time.time() >= hard_deadline:
            notes.append(f"硬超时保险丝触发（{args.max_hours}h），安全停止所有线。")
            for line in plan["lines"].values():
                if line.get("status") == "RUNNING":
                    stop_single_line(plan, node, line, "hard_deadline")
                    line.update(status="STOPPED", paused_reason="hard deadline",
                                pid=None, last_activity=iso_now())
            save_registry(reg)
            break
        if datetime.now() >= deadline:
            notes.append(f"到达 stop_at（{deadline.strftime('%H:%M')}），"
                         f"安全停止所有运行中线。")
            for line in plan["lines"].values():
                if line.get("status") == "RUNNING":
                    stop_single_line(plan, node, line, "stop_at_deadline")
                    line.update(status="STOPPED", paused_reason="deadline",
                                pid=None, last_activity=iso_now())
            save_registry(reg)
            break
        time.sleep(max(30, int(args.interval)))

    path = write_report(reg, plan, node, peaks, time.time() - started, notes)
    audit_log(f"NIGHT_DONE plan={plan['plan_id']} report={path}")
    print(f"[watch] 晨间报告：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
