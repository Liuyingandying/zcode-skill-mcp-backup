#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 NightPlan 分批错峰启动生产线（底层调用现有 Production Node）。

安全规则：
  - 同 tag 已有存活进程 → 拒绝（防双启动；state 文件锁不是给你这么用的）
  - run 目录已存在且未完成 → 拒绝并提示走 resume_lines.py（不覆盖、不 fresh）
  - run 目录存在但没有 state.json → 拒绝（脏目录需人工处理）
  - 已完成的线跳过（永不重跑）
  - 每条线启动前重新过资源门禁；门禁不放行则余下线保持 PLANNED
  - 错峰启动（默认 45s），避免瞬时 commit 峰值重演 key_2001

用法：
  python launch_lines.py --plan night_20260927 [--only scifi_01,mystery_01]
                         [--stagger 45] [--dry-run] [--skip-probe] [--probe-real]
退出码：0=全部处理，1=部分被门禁/规则拒绝，2=前置失败（无计划/无 Node/探测失败）
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nff_common import (audit_log, classify_launch, counts_from_units,  # noqa: E402
                        evaluate_gate, find_node_root, iso_now, judge_counts,
                        list_python_processes, load_registry, logs_dir,
                        match_line_pids, probe_provider, query_memory, read_state,
                        reconfigure_stdio, resolve_provider, run_dir_for,
                        save_registry, spawn_detached)
from plan_night import register_plan, validate_plan  # noqa: E402

ENGINE_ENTRY = os.path.join("experiments", "multi_worker_generation", "run.py")


def probe_real(root: Path, prof: dict) -> tuple[bool, str]:
    """真实最小 LLM 调用（node_check.py probe），破 /health 假绿。"""
    cmd = [sys.executable, os.path.join("production_node", "node_check.py"),
           "probe", "--key-env", prof["key_env_name"], "--timeout", str(prof["timeout_s"])]
    if prof["model"]:
        cmd += ["--model", prof["model"]]
    try:
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        tail = (r.stdout or r.stderr or "").strip().splitlines()
        return ok, (tail[-1] if tail else f"exit={r.returncode}")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="错峰启动 NightPlan 生产线")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--plan-file", default=None, help="从计划文件注册后再启动")
    ap.add_argument("--only", default=None, help="只启动这些 line_id（逗号分隔）")
    ap.add_argument("--stagger", type=int, default=45, help="两线间隔秒（20~60 推荐）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-probe", action="store_true", help="跳过网络探测（不推荐）")
    ap.add_argument("--probe-real", action="store_true",
                    help="加一次真实最小 LLM 调用（node_check probe）")
    args = ap.parse_args()

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None and args.plan_file:
        plan = json.loads(Path(args.plan_file).read_text(encoding="utf-8"))
        errs = validate_plan(plan)
        if errs:
            for e in errs:
                print(f"[launch] 计划文件校验失败：{e}")
            return 2
        register_plan(plan)
    if plan is None:
        print(f"[launch] 未找到计划：{args.plan}（可先 plan_night.py build）")
        return 2

    node, msg = find_node_root()
    if node is None:
        print(f"[launch] {msg}")
        return 2
    prof = resolve_provider(plan.get("provider", "glm"))

    if not args.skip_probe:
        net = probe_provider(prof["base_url"])
        print(f"[launch] 网络探测：tcp={net.get('tcp')} {net.get('host')}:{net.get('port')}"
              + (f"（{net.get('reason')}）" if net.get("reason") else ""))
        if net.get("tcp") is not True:
            print("[launch] 网关不可达，拒绝启动。"
                  "可先 `control_center.gateway.ensure_gateway()` 或手动拉起网关后重试。")
            return 2
        if args.probe_real:
            ok, detail = probe_real(node, prof)
            print(f"[launch] 真实探测（node_check probe）：{'OK' if ok else 'FAIL'} {detail}")
            if not ok:
                return 2

    only = set(x.strip() for x in (args.only or "").split(",") if x.strip())
    try:
        procs = list_python_processes()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        procs = []
        print(f"[launch] 进程表获取失败（按空表处理）：{e}")

    def mem_gate():
        try:
            return evaluate_gate(query_memory())
        except OSError:
            return None

    launched, refused, remaining = [], [], []
    gate = mem_gate()
    if gate and not gate["allow_new_line"]:
        print("[launch] 资源门禁未放行：")
        for r in gate["reasons"]:
            print(f"  - {r}")
        return 1

    for lid, line in sorted(plan["lines"].items()):
        if only and lid not in only:
            continue
        if line.get("status") not in ("PLANNED",):
            refused.append((lid, f"状态 {line['status']} 非 PLANNED"
                                 f"（续跑用 resume_lines.py）"))
            continue
        rd = run_dir_for(node, line["tag"])
        state = read_state(node, line["tag"])
        live = match_line_pids(procs, line["tag"], rd)
        kind = classify_launch(rd, state, len(live), line["target"])
        if kind == "completed":
            counts = counts_from_units(state.get("units", []))
            line.update(status=judge_counts(counts, line["target"]),
                        done=counts.get("done", 0), failed=counts.get("failed", 0),
                        pending=counts.get("pending", 0), claimed=counts.get("claimed", 0),
                        recovered_success=counts.get("recovered_success", 0),
                        run_dir=str(rd), last_activity=iso_now(),
                        notes=line.get("notes", []) + ["启动时发现已完成，跳过"])
            refused.append((lid, "已完成，跳过（永不重跑）"))
            continue
        if kind == "already_running":
            line.update(status="RUNNING", run_dir=str(rd), last_activity=iso_now())
            refused.append((lid, f"该 tag 已有存活进程 {live}，拒绝双启动"))
            continue
        if kind == "resumable":
            refused.append((lid, "存在未完成 state，请用 resume_lines.py 续跑（不覆盖）"))
            continue
        if kind == "block_leftover":
            refused.append((lid, "run 目录存在但无 state.json（脏目录），需人工处理"))
            continue

        # fresh：启动前最后一道门禁
        g = mem_gate()
        if g and not g["allow_new_line"]:
            remaining.append(lid)
            print(f"[launch] 门禁收紧，{lid} 及之后各线保持 PLANNED：")
            for r in g["reasons"]:
                print(f"  - {r}")
            break

        cmd = [sys.executable, ENGINE_ENTRY, "--limit", str(line["target"]),
               "--workers", str(line["workers"]), "--tag", line["tag"]]
        log = logs_dir() / f"{line['tag']}.launch.log"
        if args.dry_run:
            print(f"[launch][dry-run] {lid}: {' '.join(cmd)}  (cwd={node}, log={log})")
            continue
        pid = spawn_detached(cmd, cwd=node, log_path=log)
        line.update(status="RUNNING", pid=pid, started_at=iso_now(), run_dir=str(rd),
                    launch_log=str(log), last_activity=iso_now(),
                    pending=line["target"], notes=line.get("notes", []))
        launched.append((lid, pid))
        audit_log(f"LINE_LAUNCHED plan={plan['plan_id']} line={lid} tag={line['tag']} "
                  f"pid={pid} workers={line['workers']}")
        print(f"[launch] {lid} 已启动 pid={pid} tag={line['tag']} "
              f"workers={line['workers']} target={line['target']}")
        if launched and len(plan["lines"]) > 1:
            time.sleep(max(5, min(int(args.stagger), 120)))

    save_registry(reg)
    print(f"[launch] 完成：新启 {len(launched)}，拒绝/跳过 {len(refused)}，"
          f"待扩容 {len(remaining)}")
    for lid, why in refused:
        print(f"  - {lid}: {why}")
    return 0 if not refused and not remaining else (0 if launched or args.dry_run else 1)


if __name__ == "__main__":
    raise SystemExit(main())
