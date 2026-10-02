#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恢复未完成生产线（固化已验证的 resume 规则）。

规则（不得违反）：
  done / recovered_success   → 永远跳过（终态）
  claimed stale              → 由引擎 resume 时回收：先查产物，完整→恢复成功，否则→pending
  failed                     → 不自动重试。无 --retry-failed 时报告
                                FAILED_UNITS_REQUIRE_EXPLICIT_RETRY
  恢复动作 = 同 tag 重发原命令（引擎 init_batch 幂等，绝不覆盖 state）
  显式重试 = --retry-failed --yes-rewrite-state：先备份 state.json，再把
  failed→pending（attempts 归零），写审计日志——绝不静默篡改 state

用法：
  python resume_lines.py --plan night_20260927 [--line scifi_01]
                         [--no-recover] [--retry-failed --yes-rewrite-state]
                         [--dry-run]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (audit_log, atomic_write_text, evaluate_gate,  # noqa: E402
                        find_node_root, iso_now, judge_counts, list_python_processes,
                        load_registry, match_line_pids, query_memory, read_state_counts,
                        reconfigure_stdio, rewrite_failed_to_pending, run_dir_for,
                        save_registry, spawn_detached, stale_claimed, state_path_for)

ENGINE_ENTRY = os.path.join("experiments", "multi_worker_generation", "run.py")
RESUMABLE_FROM = ("STOPPED", "PAUSED_UPSTREAM", "PAUSED_RESOURCE", "FAILED_RESUMABLE")


def recover_only(root: Path, tag: str, target: int, timeout: int = 600) -> tuple[bool, str]:
    """run.py --recover-only：只做磁盘产物恢复（不调 LLM）。"""
    cmd = [sys.executable, ENGINE_ENTRY, "--recover-only", "--limit", str(target),
           "--tag", tag]
    try:
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                           timeout=timeout)
        tail = (r.stdout or r.stderr or "").strip().splitlines()
        return r.returncode == 0, (tail[-1] if tail else f"exit={r.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def relaunch(root: Path, line: dict, dry_run: bool) -> int | None:
    cmd = [sys.executable, ENGINE_ENTRY, "--limit", str(line["target"]),
           "--workers", str(line["workers"]), "--tag", line["tag"], "--resume"]
    log = Path(line.get("launch_log") or
               (Path.home() / ".night-fiction-factory" / "logs" / f"{line['tag']}.launch.log"))
    if dry_run:
        print(f"[resume][dry-run] {line['line_id']}: {' '.join(cmd)}")
        return -1
    return spawn_detached(cmd, cwd=root, log_path=log)


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="恢复未完成生产线")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--line", default=None, help="只恢复该 line_id")
    ap.add_argument("--no-recover", action="store_true", help="跳过 recover-only 预恢复")
    ap.add_argument("--retry-failed", action="store_true",
                    help="显式重试 failed 单元（必须同时给 --yes-rewrite-state）")
    ap.add_argument("--yes-rewrite-state", action="store_true",
                    help="确认允许改写 state.json（先自动备份）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.retry_failed and not args.yes_rewrite_state:
        print("[resume] --retry-failed 必须搭配 --yes-rewrite-state"
              "（会先备份 state.json 再改写，写审计日志）")
        return 2

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[resume] 未找到计划：{args.plan}")
        return 2
    node, msg = find_node_root()
    if node is None:
        print(f"[resume] {msg}")
        return 2
    try:
        gate = evaluate_gate(query_memory())
    except OSError:
        gate = None

    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        procs = []

    resumed, refused, need_explicit = [], [], []
    for lid, line in sorted(plan["lines"].items()):
        if args.line and lid != args.line:
            continue
        if line.get("status") == "PLANNED":
            refused.append((lid, "从未启动，请用 launch_lines.py"))
            continue
        state, counts = read_state_counts(node, line["tag"])
        if state is None:
            refused.append((lid, "无 state.json，无法恢复"))
            continue
        live = match_line_pids(procs, line["tag"], run_dir_for(node, line["tag"]))
        if live:
            refused.append((lid, f"仍在运行 {live}，跳过"))
            continue

        # 1) recover-only 预恢复（磁盘有完整产物但状态 failed/pending → recovered_success）
        if not args.no_recover:
            ok, detail = recover_only(node, line["tag"], line["target"])
            print(f"[resume] {lid} recover-only：{'OK' if ok else 'FAIL'} {detail}")
            state, counts = read_state_counts(node, line["tag"])
            if state is None:
                refused.append((lid, "recover 后 state 仍缺失"))
                continue

        judged = judge_counts(counts, line["target"])
        stales = len(stale_claimed(state.get("units", [])))
        failed_n = counts.get("failed", 0)

        if judged in ("COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS"):
            line.update(status=judged, done=counts.get("done", 0),
                        failed=failed_n, pending=counts.get("pending", 0),
                        claimed=counts.get("claimed", 0),
                        recovered_success=counts.get("recovered_success", 0),
                        pid=None, last_activity=iso_now())
            refused.append((lid, f"已是终态 {judged}"))
            continue

        # 2) failed 处置
        if failed_n > 0 and not args.retry_failed:
            need_explicit.append((lid, failed_n))
            print(f"[resume] {lid}: FAILED_UNITS_REQUIRE_EXPLICIT_RETRY"
                  f"（{failed_n} 个 failed 单元未被重试；"
                  f"如需重跑请 --retry-failed --yes-rewrite-state）")
        if failed_n > 0 and args.retry_failed:
            sp = state_path_for(node, line["tag"])
            bak = sp.with_name(f"state.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
            shutil.copy2(sp, bak)
            n = rewrite_failed_to_pending(state)
            atomic_write_text(sp, json.dumps(state, ensure_ascii=False, indent=2))
            audit_log(f"STATE_REWRITE plan={args.plan} line={lid} tag={line['tag']} "
                      f"failed->pending n={n} backup={bak}")
            print(f"[resume] {lid}: 显式重试已应用（{n} 个 failed→pending，备份 {bak.name}）")
            state, counts = read_state_counts(node, line["tag"])

        # 3) 还有活干吗？
        pending_n = counts.get("pending", 0)
        claimed_n = counts.get("claimed", 0)
        if pending_n == 0 and claimed_n == 0 and stales == 0:
            judged = judge_counts(counts, line["target"])
            line.update(status=judged, pid=None, last_activity=iso_now(),
                        done=counts.get("done", 0), failed=counts.get("failed", 0),
                        pending=0, claimed=0,
                        recovered_success=counts.get("recovered_success", 0))
            refused.append((lid, f"无待执行单元（judged={judged}），无需重启"))
            continue

        # 4) 资源门禁
        if gate and not gate["allow_new_line"]:
            line.update(status="PAUSED_RESOURCE",
                        paused_reason="；".join(gate["reasons"]), last_activity=iso_now())
            refused.append((lid, "资源门禁未放行，已标记 PAUSED_RESOURCE"))
            continue

        pid = relaunch(node, line, args.dry_run)
        if pid:
            line.update(status="RUNNING", pid=None if pid < 0 else pid,
                        started_at=iso_now(), last_activity=iso_now(),
                        restarts=line.get("restarts", 0) + 1,
                        done=counts.get("done", 0), failed=counts.get("failed", 0),
                        pending=pending_n, claimed=claimed_n,
                        recovered_success=counts.get("recovered_success", 0),
                        paused_reason=None)
            resumed.append((lid, pid))
            audit_log(f"LINE_RESUMED plan={args.plan} line={lid} tag={line['tag']} pid={pid}")
            print(f"[resume] {lid} 已续跑 pid={pid}（pending={pending_n}, "
                  f"claimed={claimed_n}, stale={stales}, failed={failed_n}）")

    save_registry(reg)
    print(f"[resume] 完成：续跑 {len(resumed)}，跳过 {len(refused)}")
    for lid, why in refused:
        print(f"  - {lid}: {why}")
    if need_explicit:
        print("[resume] 提示：failed 单元永远不会被静默重试。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
