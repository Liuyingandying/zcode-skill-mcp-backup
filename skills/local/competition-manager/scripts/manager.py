#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Competition Manager —— 数学建模比赛任务管理 CLI（纯本地，无外部 API）
数据契约见 references/design.md；用法: python manager.py {add,evaluate,plan,track,list,report} -h
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_FILE = "competitions.json"
PROJ_ROOT = "competitions"
PLANS_DIR = "plans"

STAGES = ["problem-analysis", "modeling", "coding", "writing", "review"]
STAGE_WEIGHTS = {"problem-analysis": 0.15, "modeling": 0.25,
                 "coding": 0.30, "writing": 0.25, "review": 0.05}

# 本地能力表（源自 2026-09-24 环境审计，赛前可手动更新）
TOOL_AVAILABILITY = {
    "python": True, "pandas": True, "numpy": True, "scipy": True, "matplotlib": True,
    "sklearn": True, "statsmodels": True, "cvxpy": True, "pulp": True,
    "lightgbm": True, "xgboost": True, "latex": True,
    "matlab": False, "gurobi": False, "typst": False, "r": False, "spss": False,
}

LEVEL_TABLE = [("国家级A", 30), ("国赛", 30), ("美赛", 28), ("国际", 26),
               ("国家级B", 24), ("省级", 18), ("市级", 14), ("校级", 10)]

SCAFFOLD = {
    "00_admin/README.md": "# 报名信息 / 官方规则 / 截止时间线\n",
    "10_problem/README.md": "# 题目原文、附件、题面解析\n",
    "20_data/raw/.gitkeep": "",
    "20_data/processed/.gitkeep": "",
    "30_models/README.md": "# 建模方案（2analysis-modeling -> ANALYSIS_MODELING_REPORT.md 落此处）\n",
    "40_exp/README.md": "# 实验代码工作区（3coding-visual / 4drawio）\n",
    "50_results/README.md": "# RESULTS_REPORT.md + figures/（4drawio 流程图 PDF 也放 figures/）\n",
    "60_paper/README.md": "# 论文源（5writing：main.tex / typst）与编译产物\n",
    "70_review/README.md": "# 验收记录（6verity / mmc-helper 三查两证）\n",
    "archive/.gitkeep": "",
}


# ---------- 数据层 ----------
def load(root: Path) -> dict:
    f = root / DB_FILE
    if not f.exists():
        return {"version": 1, "updated": str(date.today()),
                "profile": {"team_size": 3, "hours_per_week": 20, "skill_level": 3},
                "competitions": []}
    return json.loads(f.read_text(encoding="utf-8"))


def save(root: Path, db: dict) -> None:
    db["updated"] = str(date.today())
    (root / DB_FILE).write_text(
        json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_date(s: str) -> date:
    return date.fromisoformat(s.strip())


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name).strip("-")
    return s[:20] or "project"


# ---------- 项目脚手架 ----------
def create_project(root: Path, comp: dict) -> str:
    proj_rel = f"{PROJ_ROOT}/{comp['id']}-{slugify(comp['competition_name'])}"
    proj = root / proj_rel
    proj.mkdir(parents=True, exist_ok=True)
    for rel, content in SCAFFOLD.items():
        p = proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    project = {
        "id": comp["id"],
        "competition_name": comp["competition_name"],
        "deadline": comp["deadline"],
        "created": str(date.today()),
        "current_stage": "registered",
        "history": [{"date": str(date.today()), "event": "project created"}],
        "notes": [],
    }
    (proj / "project.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return proj_rel


# ---------- 评估模型 ----------
def score(comp: dict, profile: dict) -> dict:
    today = date.today()
    deadline = parse_date(comp["deadline"])
    days_left = (deadline - today).days

    level = comp.get("level", "")
    value = next((pts for key, pts in LEVEL_TABLE if key in str(level)),
                 15 if level else 12)

    effort_days = 4 + 2 * int(comp["difficulty"])
    if days_left < 0:
        time_score, time_note = 0, "已截止"
    else:
        ratio = days_left / effort_days
        time_score = round(30 * min(max((ratio - 0.5) / 1.0, 0.0), 1.0))
        time_note = f"剩{days_left}天/需约{effort_days}天" + \
            ("" if ratio >= 1.0 else " ⚠时间不足")

    diff_fit = max(0, 20 - 7 * abs(int(comp["difficulty"]) - int(profile.get("skill_level", 3))))

    tools = comp.get("required_tools", []) or []
    known = [t for t in tools if t in TOOL_AVAILABILITY]
    ratio_t = sum(1.0 if TOOL_AVAILABILITY[t] else 0.0 for t in known) / len(tools) if tools else 1.0
    unknown = [t for t in tools if t not in TOOL_AVAILABILITY]
    ratio_t = (ratio_t * len(known) + 0.5 * len(unknown)) / len(tools) if tools else 1.0
    tools_score = round(20 * ratio_t)
    missing = [t for t in known if not TOOL_AVAILABILITY[t]]

    total = value + time_score + diff_fit + tools_score
    if days_left < 0:
        decision = "已截止(expired)"
    elif total >= 75:
        decision = "强烈推荐"
    elif total >= 55:
        decision = "推荐"
    elif total >= 35:
        decision = "备选观察"
    else:
        decision = "不建议"

    return {
        "worth_score": total,
        "decision": decision,
        "score_breakdown": {"value": value, "time": time_score,
                            "difficulty_fit": diff_fit, "tools": tools_score},
        "_notes": [time_note] + ([f"工具缺失: {', '.join(missing)}"] if missing else []),
    }


# ---------- 子命令 ----------
def cmd_add(args, root: Path, db: dict) -> None:
    comps = db["competitions"]
    comp = {
        "id": f"C-{len(comps) + 1:03d}",
        "competition_name": args.name,
        "deadline": str(parse_date(args.deadline)),
        "category": args.category,
        "difficulty": args.difficulty,
        "topic": args.topic,
        "required_tools": [t.strip() for t in args.tools.split(",") if t.strip()],
        "status": "discovered",
        "level": args.level or "",
    }
    comp["project_dir"] = create_project(root, comp)
    comps.append(comp)
    save(root, db)
    print(f"[OK] {comp['id']} 已录入并创建项目目录: {comp['project_dir']}")


def cmd_evaluate(args, root: Path, db: dict) -> None:
    rows = []
    for c in db["competitions"]:
        if c.get("status") in ("submitted", "dropped"):
            continue
        r = score(c, db.get("profile", {}))
        c.update(worth_score=r["worth_score"], decision=r["decision"],
                 score_breakdown=r["score_breakdown"])
        rows.append((c, r["_notes"]))
    save(root, db)
    print(f"{'ID':6} {'worth':>5}  {'决策':10} 价值/时间/难度/工具  备注")
    print("-" * 72)
    for c, notes in sorted(rows, key=lambda x: -x[0]["worth_score"]):
        b = c["score_breakdown"]
        print(f"{c['id']:6} {c['worth_score']:>5}  {c['decision']:10} "
              f"{b['value']:>3}/{b['time']:>3}/{b['difficulty_fit']:>3}/{b['tools']:>3}"
              f"   {'; '.join(notes)}")
    print("-" * 72)
    print("提示: 评估仅为启发式建议，参赛决策由你做出。")


def cmd_plan(args, root: Path, db: dict) -> None:
    today = date.today()
    accepted = [c for c in db["competitions"]
                if c.get("worth_score") is not None and "不建议" not in c["decision"]
                and "已截止" not in c["decision"] and c.get("status") not in ("submitted", "dropped")]
    accepted.sort(key=lambda c: -c["worth_score"])
    lines = [f"# 参赛执行计划（生成于 {today}）", "",
             f"共评估 {len(db['competitions'])} 项，纳入计划 {len(accepted)} 项，按 worth 降序：", ""]

    windows = []
    for rank, c in enumerate(accepted, 1):
        deadline = parse_date(c["deadline"])
        effort = 4 + 2 * int(c["difficulty"])
        start = deadline - timedelta(days=effort + 1)
        windows.append((c["id"], start, deadline))
        lines += [f"## #{rank} {c['id']} {c['competition_name']} "
                  f"(worth {c['worth_score']} · {c['decision']})", ""]
        lines.append(f"- 主题: {c['topic']} ｜ 类别: {c['category']} ｜ 截止: {c['deadline']}")
        if start > today:
            lines.append(f"- 建议启动: **{start}**（截止前 {effort + 1} 天）")
        else:
            lines.append(f"- ⚠ 启动日已过（计算值 {start}）→ 若参加需**立即启动**或放弃")
        lines.append("- 阶段计划:")
        cur = max(start, today)
        for st in STAGES:
            d = max(1, round(effort * STAGE_WEIGHTS[st]))
            if cur > deadline:
                lines.append(f"  - ⚠ {st}（{d} 天）已超出截止日 → 需压缩前置阶段或放弃")
                continue
            seg_end = min(cur + timedelta(days=d - 1), deadline)
            flag = "" if seg_end == cur + timedelta(days=d - 1) else " ⚠被截止截断"
            lines.append(f"  - {cur} ~ {seg_end}  {st}（{d} 天）{flag}")
            cur = seg_end + timedelta(days=1)
        b = c["score_breakdown"]
        lines.append(f"- 评分构成: 价值{b['value']} + 时间{b['time']} + 难度{b['difficulty_fit']} + 工具{b['tools']}")
        lines.append("")

    lines.append("## 冲突与风险")
    conflicts = [(a, b) for i, a in enumerate(windows) for b in windows[i + 1:]
                 if a[1] <= b[2] and b[1] <= a[2]]
    lines += [f"- ⚠ 时间窗重叠: {a[0]} × {b[0]}" for a, b in conflicts] or \
             ["- 各比赛时间窗无重叠，可顺序执行"]
    for c in accepted:
        miss = [t for t in c["required_tools"]
                if t in TOOL_AVAILABILITY and not TOOL_AVAILABILITY[t]]
        if miss:
            lines.append(f"- ⚠ {c['id']} 缺工具: {', '.join(miss)}（安装或换队内资源）")
    text = "\n".join(lines)
    print(text)
    if args.save:
        out = root / PLANS_DIR
        out.mkdir(exist_ok=True)
        p = out / f"plan-{today}.md"
        p.write_text(text, encoding="utf-8")
        print(f"\n[OK] 计划已保存: {p}")


def cmd_track(args, root: Path, db: dict) -> None:
    comp = next((c for c in db["competitions"] if c["id"] == args.id), None)
    if not comp:
        sys.exit(f"[FAIL] 未找到 {args.id}")
    if args.status:
        comp["status"] = args.status
    proj = root / comp["project_dir"] / "project.json"
    project = json.loads(proj.read_text(encoding="utf-8"))
    if args.stage:
        project["current_stage"] = args.stage
    event = {"date": str(date.today()),
             "event": f"status={args.status or '不变'} stage={args.stage or '不变'} note={args.note or ''}"}
    project["history"].append(event)
    if args.note:
        project["notes"].append(f"{date.today()} {args.note}")
    proj.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    save(root, db)
    print(f"[OK] {args.id} -> status={comp['status']} stage={project['current_stage']}")


def cmd_list(args, root: Path, db: dict) -> None:
    print(f"{'ID':6} {'status':12} {'deadline':11} {'diff':4} {'worth':>5}  名称")
    print("-" * 78)
    for c in db["competitions"]:
        print(f"{c['id']:6} {c['status']:12} {c['deadline']:11} {c['difficulty']:<4} "
              f"{str(c.get('worth_score', '-')):>5}  {c['competition_name']}")


def cmd_report(args, root: Path, db: dict) -> None:
    cmd_list(args, root, db)
    print()
    from collections import Counter
    dist = Counter(c["status"] for c in db["competitions"])
    print("状态分布:", ", ".join(f"{k}×{v}" for k, v in dist.items()))
    for c in db["competitions"]:
        pj = root / c["project_dir"] / "project.json"
        if pj.exists():
            p = json.loads(pj.read_text(encoding="utf-8"))
            print(f"  {c['id']}: stage={p['current_stage']}, 历史事件 {len(p['history'])} 条")


def main() -> None:
    ap = argparse.ArgumentParser(description="Competition Manager（纯本地比赛任务管理）")
    ap.add_argument("--root", default=".", help="工作区根目录（数据库所在处），默认当前目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="录入比赛并创建项目目录")
    p.add_argument("--name", required=True)
    p.add_argument("--deadline", required=True, help="YYYY-MM-DD")
    p.add_argument("--category", required=True)
    p.add_argument("--difficulty", type=int, choices=range(1, 6), default=3)
    p.add_argument("--topic", required=True)
    p.add_argument("--tools", default="python", help="逗号分隔")
    p.add_argument("--level", default="", help="如 国家级A/省级/校级")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("evaluate", help="评估是否值得参加")
    p.set_defaults(fn=cmd_evaluate)

    p = sub.add_parser("plan", help="排序 + 执行计划")
    p.add_argument("--save", action="store_true")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("track", help="更新进度")
    p.add_argument("--id", required=True)
    p.add_argument("--status")
    p.add_argument("--stage")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_track)

    for name in ("list", "report"):
        p = sub.add_parser(name)
        p.set_defaults(fn={"list": cmd_list, "report": cmd_report}[name])

    args = ap.parse_args()
    root = Path(args.root).resolve()
    db = load(root)
    args.fn(args, root, db)


if __name__ == "__main__":
    main()
