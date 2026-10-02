#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NightPlan 构建与校验。

自然语言 → NightPlan 的"理解"由 Z Code 会话完成；本脚本负责把已明确的
参数落成结构化计划：生成唯一 tag、计算 worker 预算、写 plans/ 与注册簿。

用法：
  python plan_night.py build --lines 6 --genres "科幻,悬疑,都市,奇幻,乡土,童话" \
      --total 1200 --stop-at 08:00 --provider glm --max-total-workers 12
  python plan_night.py build --lines 3 --targets "200,200,100" ...
  python plan_night.py validate --plan night_20260927
  python plan_night.py show    --plan night_20260927

注意：line.genre 当前是**组织标签**（引擎按内建比例混合题材，无 line-specific
注入通道）；genre_mode 固定记为 label_only，不得伪造成注入能力。
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nff_common import (TAG_RE, allocate_workers, atomic_write_text, audit_log,
                        evaluate_gate, find_node_root, iso_now, load_registry,
                        parse_stop_at, plans_dir, query_memory, reconfigure_stdio,
                        run_dir_for, sanitize_slug, save_registry)  # noqa: E402


def build_plan(opts: dict) -> tuple[dict, list]:
    """纯逻辑（内存查询可通过 opts['memory'] 注入）。返回 (plan, warnings)。"""
    warnings: list = []
    n_lines = int(opts["lines"])
    if n_lines < 1:
        raise SystemExit("--lines 至少 1")
    base_genres = [g.strip() for g in (opts.get("genres") or "").split(",") if g.strip()]
    if not base_genres:
        base_genres = ["mixed"]
    genres = list(base_genres)
    if len(base_genres) < n_lines:
        while len(genres) < n_lines:
            genres.append(f"{base_genres[len(genres) % len(base_genres)]}-{len(genres) + 1}")
        warnings.append(f"题材数少于生产线数：已循环编号"
                        f"（{n_lines} 线共用 {len(base_genres)} 个题材标签）")

    targets = []
    if opts.get("targets"):
        targets = [int(x) for x in str(opts["targets"]).split(",") if x.strip()]
        if len(targets) != n_lines:
            raise SystemExit(f"--targets 数量（{len(targets)}）必须等于 --lines（{n_lines}）")
    else:
        total = int(opts["total"])
        if total < n_lines:
            raise SystemExit("--total 不能小于 --lines")
        base, rem = divmod(total, n_lines)
        targets = [base + (1 if i < rem else 0) for i in range(n_lines)]

    stop_at = opts.get("stop_at") or "08:00"
    parse_stop_at(stop_at)  # 早失败

    # tag 唯一性：计划内 + 磁盘上已存在的 run 目录
    node = opts.get("_node_root")
    date = datetime.now().strftime("%Y%m%d")
    used = set()
    lines = []
    for i in range(n_lines):
        slug = sanitize_slug(genres[i])
        seq = 1
        while True:
            tag = f"night_{date}_{slug}_{seq:02d}"
            if not TAG_RE.match(tag):
                raise SystemExit(f"tag 不合法：{tag}")
            if tag in used:
                seq += 1
                continue
            if node is not None and Path(run_dir_for(node, tag)).exists():
                seq += 1
                continue
            used.add(tag)
            break
        lines.append({"line_id": f"{slug}_{seq:02d}",
                      "tag": tag, "genre": genres[i], "target": targets[i],
                      "workers": 0, "status": "PLANNED"})

    memory = opts.get("memory")
    if memory is None:
        try:
            memory = query_memory()
        except OSError:
            warnings.append("无法查询内存（非 Windows 或 API 失败）：按 max_total_workers 直接分配")
    gate = evaluate_gate(memory) if memory else None
    if gate and not gate["allow_new_line"]:
        warnings.append("资源门禁未放行：" + "；".join(gate["reasons"]) + "（计划已写，launch 会拒绝）")
    alloc, budget = allocate_workers(n_lines, int(opts["max_total_workers"]),
                                     memory=memory, per_line_cap=int(opts["per_line_cap"]))
    for line, w in zip(lines, alloc):
        line["workers"] = w
    zero = [l["line_id"] for l in lines if l["workers"] == 0]
    if zero:
        warnings.append(f"worker 预算不足，以下线保持 PLANNED 待扩容：{', '.join(zero)}")

    plan = {"plan_id": opts["plan_id"] or f"night_{date}",
            "created_at": iso_now(),
            "provider": opts["provider"],
            "model": opts.get("model") or "",
            "start_mode": opts.get("start_mode") or "now",
            "stop_at": stop_at,
            "max_total_workers": int(opts["max_total_workers"]),
            "per_line_cap": int(opts["per_line_cap"]),
            "genre_mode": "label_only",
            "allocation_budget": budget,
            "lines": {l["line_id"]: l for l in lines}}
    return plan, warnings


def validate_plan(plan: dict) -> list:
    errs = []
    if not plan.get("plan_id"):
        errs.append("缺少 plan_id")
    if plan.get("provider") not in ("glm", "tju", "custom_openai_compatible"):
        errs.append(f"provider 非法：{plan.get('provider')}")
    lines = plan.get("lines") or {}
    if not lines:
        errs.append("lines 为空")
    tags = set()
    for lid, l in lines.items():
        for k in ("tag", "target", "workers"):
            if k not in l:
                errs.append(f"{lid} 缺少 {k}")
        if not TAG_RE.match(str(l.get("tag", ""))):
            errs.append(f"{lid} tag 非法：{l.get('tag')}")
        if l.get("tag") in tags:
            errs.append(f"tag 重复：{l.get('tag')}")
        tags.add(l.get("tag"))
        if int(l.get("target", 0)) < 1:
            errs.append(f"{lid} target 必须 >=1")
        if int(l.get("workers", 0)) > 9:
            errs.append(f"{lid} workers 超过引擎上限 9（config.json worker 列表长度）")
    if plan.get("genre_mode") != "label_only":
        errs.append("genre_mode 必须是 label_only（引擎当前无 line-specific 注入通道，不得伪造）")
    return errs


def register_plan(plan: dict) -> None:
    reg = load_registry()
    plan_reg = json.loads(json.dumps(plan, ensure_ascii=False))
    for lid, l in plan_reg["lines"].items():
        l.setdefault("pid", None)
        l.setdefault("started_at", None)
        l.setdefault("last_activity", None)
        l.setdefault("done", 0)
        l.setdefault("failed", 0)
        l.setdefault("pending", l["target"])
        l.setdefault("claimed", 0)
        l.setdefault("recovered_success", 0)
        l.setdefault("run_dir", None)
        l.setdefault("launch_log", None)
        l.setdefault("paused_reason", None)
        l.setdefault("breach_count", 0)
        l.setdefault("restarts", 0)
        l.setdefault("notes", [])
    reg["plans"][plan_reg["plan_id"]] = plan_reg
    save_registry(reg)
    atomic_write_text(plans_dir() / f"{plan_reg['plan_id']}.json",
                      json.dumps(plan_reg, ensure_ascii=False, indent=2))
    audit_log(f"PLAN_CREATED {plan_reg['plan_id']} lines={len(plan_reg['lines'])}")


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="NightPlan 构建/校验")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build")
    b.add_argument("--lines", type=int, required=True)
    b.add_argument("--genres", default="", help="逗号分隔题材标签（仅组织标签，非注入）")
    b.add_argument("--total", type=int, help="总篇数（均分到各线）")
    b.add_argument("--targets", help="逗号分隔各线篇数（与 --total 二选一）")
    b.add_argument("--stop-at", default="08:00")
    b.add_argument("--provider", default="glm",
                   choices=["glm", "tju", "custom_openai_compatible"])
    b.add_argument("--model", default="")
    b.add_argument("--start-mode", default="now", choices=["now", "at"])
    b.add_argument("--max-total-workers", type=int, default=12)
    b.add_argument("--per-line-cap", type=int, default=9)
    b.add_argument("--plan-id", default=None)

    v = sub.add_parser("validate")
    v.add_argument("--plan", required=True)
    v.add_argument("--file", default=None, help="直接校验计划文件而不读注册簿")

    s = sub.add_parser("show")
    s.add_argument("--plan", required=True)
    args = ap.parse_args()

    if args.cmd == "build":
        node, msg = find_node_root()
        opts = dict(lines=args.lines, genres=args.genres, total=args.total,
                    targets=args.targets, stop_at=args.stop_at, provider=args.provider,
                    model=args.model, start_mode=args.start_mode,
                    max_total_workers=args.max_total_workers,
                    per_line_cap=args.per_line_cap, plan_id=args.plan_id,
                    _node_root=node)
        plan, warnings = build_plan(opts)
        errs = validate_plan(plan)
        if errs:
            for e in errs:
                print(f"[plan] 校验失败：{e}")
            return 2
        register_plan(plan)
        print(f"[plan] {plan['plan_id']} 已写入（{len(plan['lines'])} 线，"
              f"总目标 {sum(l['target'] for l in plan['lines'].values())} 篇，"
              f"worker 预算 {plan['allocation_budget']}）")
        for lid, l in plan["lines"].items():
            print(f"  {lid:<14} tag={l['tag']:<32} genre={l['genre']:<6} "
                  f"target={l['target']:<5} workers={l['workers']}")
        for w in warnings:
            print(f"  ! {w}")
        return 0

    if args.cmd == "validate":
        if args.file:
            plan = json.loads(Path(args.file).read_text(encoding="utf-8"))
        else:
            reg = load_registry()
            plan = reg.get("plans", {}).get(args.plan)
            if plan is None:
                print(f"[plan] 未找到计划：{args.plan}")
                return 2
        errs = validate_plan(plan)
        if errs:
            for e in errs:
                print(f"[plan] {e}")
            return 1
        print(f"[plan] {plan['plan_id']} 校验通过（{len(plan['lines'])} 线）")
        return 0

    reg = load_registry()
    plan = reg.get("plans", {}).get(args.plan)
    if plan is None:
        print(f"[plan] 未找到计划：{args.plan}")
        return 2
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
