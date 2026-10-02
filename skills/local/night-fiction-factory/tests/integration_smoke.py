#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端集成冒烟（零真实生成、零真实网关依赖）。

构造一个带标记文件的临时 Production Node + 两条线的合成 state/works/计量，
然后按真实 CLI 路径走一遍：plan build → status → validate → resume →
night_watch --once → stop。断言关键语义：

  - status：COMPLETED 线正确识别；RUNNING 无进程 → FAILED_RESUMABLE；
            熔断证据（OUTAGE）可见
  - validate：done 但磁盘缺 content.md 的单元被点名；终态判定正确
  - resume：failed 不被静默重试（FAILED_UNITS_REQUIRE_EXPLICIT_RETRY）；
            pending 单元同 tag 续跑；终态线跳过
  - night_watch --once：生成晨间报告文件
  - stop：无匹配进程时安全拒杀（不碰任何无关进程）

运行：python tests/integration_smoke.py   （可反复执行，用完即清理）
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
FAILURES = []


def run(args, expect=None):
    env = dict(os.environ)
    r = subprocess.run([sys.executable] + [str(SCRIPTS / args[0])] + args[1:],
                       capture_output=True, text=True, env=env, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    if expect is not None and r.returncode != expect:
        FAILURES.append(f"{' '.join(args)}: exit={r.returncode} (期望 {expect})\n{out[-800:]}")
    print(out.rstrip())
    print(f"--- exit={r.returncode} ---")
    return r


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
    else:
        print(f"[ok] {msg}")


def plant(node: pathlib.Path, tag: str, target: int, units: list,
          drop_artifact_of: str | None = None):
    rd = node / "data/multi_worker_generation/runs" / f"multi_worker_{tag}" / "mw_pilot"
    (rd / "works").mkdir(parents=True)
    (rd / "state.json").write_text(json.dumps(
        {"batch": "mw_pilot", "size": target, "status": "running", "units": units,
         "created_at": "2026-09-27T22:00:00+08:00",
         "scheduler": "multi_worker_generation"}, ensure_ascii=False), encoding="utf-8")
    for u in units:
        if u["status"] in ("done", "recovered_success"):
            w = rd / "works" / u["unit_id"]
            w.mkdir()
            (w / "content.md").write_text("正文" * 50, encoding="utf-8")
            (w / "metadata.json").write_text(json.dumps(
                {"unit_id": u["unit_id"], "work_id": u["work_id"]}), encoding="utf-8")
    if drop_artifact_of:
        (rd / "works" / drop_artifact_of / "content.md").unlink()
    return rd


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="nff_smoke_")
    node, state = pathlib.Path(tmp) / "node", pathlib.Path(tmp) / "state"
    (node / "experiments/multi_worker_generation").mkdir(parents=True)
    (node / "ops").mkdir(parents=True)
    (node / "experiments/multi_worker_generation/run.py").write_text("# dummy\n",
                                                                     encoding="utf-8")
    (node / "ops/lab_control.py").write_text("# dummy\n", encoding="utf-8")
    os.environ["NFF_STATE_DIR"] = str(state)
    os.environ["LITERARYLAB_NODE_ROOT"] = str(node)
    # 确定性：给资源门禁一个充裕的假内存（真实机器可能恰好 headroom<6GB，
    # 那时门禁拦截续跑是正确行为——见本仓库 references/failure_modes.md FM-1）
    os.environ["NFF_FAKE_MEMORY_JSON"] = json.dumps(
        {"mem_load_pct": 40, "total_phys_gb": 32, "avail_phys_gb": 16,
         "commit_limit_gb": 40, "commit_avail_gb": 20, "commit_used_gb": 20,
         "commit_pct": 50.0, "commit_headroom_gb": 20})

    print("== 1. plan build（2 线 5+4 篇）==")
    run(["plan_night.py", "build", "--lines", "2", "--genres", "科幻,悬疑",
         "--targets", "5,4", "--stop-at", "08:00"], expect=0)

    print("== 2. 种合成数据 ==")
    plant(node, "night_20260927_scifi_01", 5, [
        {"unit_id": "mw_pilot-scifi-0000", "status": "done", "work_id": "work_00000001"},
        {"unit_id": "mw_pilot-scifi-0001", "status": "done", "work_id": "work_00000002"},
        {"unit_id": "mw_pilot-scifi-0002", "status": "done", "work_id": "work_00000003"},
        {"unit_id": "mw_pilot-scifi-0003", "status": "failed",
         "error": "HTTP 502 Bad Gateway"},
        {"unit_id": "mw_pilot-scifi-0004", "status": "pending"}],
        drop_artifact_of="mw_pilot-scifi-0002")
    rd1 = node / "data/multi_worker_generation/runs/multi_worker_night_20260927_scifi_01"
    with open(rd1 / "llm_calls.jsonl", "w", encoding="utf-8") as f:
        # 真实故障形态：先 1 条非连接类错误，再连续 6 条连接类失败（结尾连续 ≥ 阈值）
        f.write(json.dumps({"ok": False, "error": "HTTP 400"}) + "\n")
        for _ in range(6):
            f.write(json.dumps({"ok": False,
                                "error": "cannot reach upstream: connection refused"}) + "\n")
    plant(node, "night_20260927_mystery_01", 4, [
        {"unit_id": f"mw_pilot-mystery-{i:04d}", "status": s,
         "work_id": f"work_{11 + i:08d}"}
        for i, s in enumerate(["done", "recovered_success", "done",
                               "recovered_success"])])
    rp = state / "night_registry.json"
    reg = json.loads(rp.read_text(encoding="utf-8"))
    for line in reg["plans"]["night_20260927"]["lines"].values():
        line.update(status="RUNNING", pid=None)
    rp.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[plant] 就绪：scifi_01=3done(1缺产物)+1failed+1pending+熔断证据；"
          "mystery_01=全终态")

    print("== 3. status --with-breaker ==")
    r = run(["status_lines.py", "--plan", "night_20260927", "--with-breaker"], expect=0)
    check("FAILED_RESUMABLE" in r.stdout, "scifi_01 进程全灭显示 FAILED_RESUMABLE")
    check("COMPLETED" in r.stdout, "mystery_01 显示 COMPLETED（4/4 全终态零失败）")
    check("OUTAGE" in r.stdout, "熔断证据 OUTAGE 可见")

    print("== 4. validate ==")
    r = run(["validate_outputs.py", "--plan", "night_20260927"], expect=1)
    check("mw_pilot-scifi-0002" in r.stdout, "缺产物单元被点名")

    print("== 5. resume（failed 必须显式拦截）==")
    r = run(["resume_lines.py", "--plan", "night_20260927"], expect=1)
    check("FAILED_UNITS_REQUIRE_EXPLICIT_RETRY" in r.stdout,
          "failed 单元不被静默重试")
    check("已是终态 COMPLETED" in r.stdout, "终态线跳过")
    check("已续跑" in r.stdout, "pending 单元同 tag 续跑")

    print("== 6. night_watch --once（晨报）==")
    run(["night_watch.py", "--plan", "night_20260927", "--once"], expect=0)
    reports = list((state / "reports").glob("NIGHT_PRODUCTION_REPORT_*.md"))
    check(bool(reports), f"晨间报告已生成：{reports[0].name if reports else '缺失'}")

    print("== 7. stop（无匹配进程 → 安全拒杀）==")
    r = run(["stop_lines.py", "--plan", "night_20260927"], expect=0)
    check("没有需要停止的存活进程" in r.stdout, "无匹配进程时不杀任何东西")

    print()
    if FAILURES:
        print(f"SMOKE FAILED（{len(FAILURES)} 项）：")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("SMOKE OK：全部语义断言通过。临时目录：", tmp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
