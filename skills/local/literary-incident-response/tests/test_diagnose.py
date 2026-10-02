# -*- coding: utf-8 -*-
"""事故诊断器测试：用合成故障场景验证识别能力。

重点不是"能跑"，而是"能识别"——每个测试构造一种真实事故形态，
断言诊断器给出正确的故障模式与级别。

运行：python tests/test_diagnose.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import diagnose as dg  # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def make_node(tmp: str, tag: str, units: list, *, llm_calls: list | None = None,
              exceptions: dict | None = None, with_artifacts: bool = True,
              size: int | None = None) -> Path:
    """构造一个合成 Production Node。"""
    node = Path(tmp)
    (node / "experiments" / "multi_worker_generation").mkdir(parents=True, exist_ok=True)
    (node / "experiments" / "multi_worker_generation" / "run.py").write_text("# dummy\n",
                                                                            encoding="utf-8")
    rd = node / "data" / "multi_worker_generation" / "runs" / f"multi_worker_{tag}"
    batch = rd / "mw_pilot"
    (batch / "works").mkdir(parents=True, exist_ok=True)
    (batch / "state.json").write_text(json.dumps(
        {"batch": "mw_pilot", "size": size if size is not None else len(units),
         "status": "running", "units": units}, ensure_ascii=False), encoding="utf-8")
    if with_artifacts:
        for u in units:
            if u.get("status") in ("done", "recovered_success"):
                w = batch / "works" / u["unit_id"]
                w.mkdir(parents=True, exist_ok=True)
                (w / "content.md").write_text("正文" * 30, encoding="utf-8")
                (w / "metadata.json").write_text(json.dumps(
                    {"unit_id": u["unit_id"],
                     "work_id": u.get("work_id", "work_00000001")}), encoding="utf-8")
    if llm_calls is not None:
        (rd / "llm_calls.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in llm_calls) + "\n",
            encoding="utf-8")
    if exceptions:
        (rd / "logs").mkdir(parents=True, exist_ok=True)
        for name, body in exceptions.items():
            (rd / "logs" / name).write_text(json.dumps(body, ensure_ascii=False),
                                            encoding="utf-8")
    return node


def find(checks: list, cid: str, tag: str | None = None) -> dict | None:
    for c in checks:
        if c["id"] == cid and (tag is None or c.get("tag") == tag):
            return c
    return None


def test_healthy():
    print("\n[1] 健康节点 → OK")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_ok", [
            {"unit_id": f"u{i}", "status": "done", "work_id": f"work_{i:08d}"}
            for i in range(4)])
        r = dg.diagnose(node, None)
        us = find(r["checks"], "unit_states", "t_ok")
        check("判定 COMPLETED", us["judged"] == "COMPLETED", us["judged"])
        check("级别 OK", us["level"] == "OK")
        art = find(r["checks"], "artifacts", "t_ok")
        check("产物完整", art["level"] == "OK", art["detail"])


def test_memory_error_detected():
    print("\n[2] MemoryError 现场 → CRITICAL / FM-01")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_mem", [
            {"unit_id": "u0", "status": "done", "work_id": "work_00000001"},
            {"unit_id": "u1", "status": "claimed", "heartbeat": time.time() - 999},
        ], exceptions={"worker_1.exception.json": {
            "worker_id": "worker_1", "error": "MemoryError",
            "traceback": "...Path.read_text... WinError 1455 页面文件太小"}})
        r = dg.diagnose(node, None)
        we = find(r["checks"], "worker_exceptions", "t_mem")
        check("识别为 CRITICAL", we["level"] == "CRITICAL", we["level"])
        check("指向 FM-01", we.get("mode") == "FM-01", str(we.get("mode")))
        check("detail 提到 MemoryError", "MemoryError" in we["detail"] or "1455" in we["detail"])


def test_stale_claimed_detected():
    print("\n[3] stale claimed → WARN / FM-04")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_stale", [
            {"unit_id": "u0", "status": "done", "work_id": "work_00000001"},
            {"unit_id": "u1", "status": "claimed", "heartbeat": time.time() - 500},
            {"unit_id": "u2", "status": "claimed"},   # 缺 heartbeat 也算 stale
            {"unit_id": "u3", "status": "pending"},
        ])
        r = dg.diagnose(node, None)
        us = find(r["checks"], "unit_states", "t_stale")
        check("识别 2 个 stale", len(us["stale_claimed"]) == 2, str(us["stale_claimed"]))
        check("指向 FM-04", us.get("mode") == "FM-04", str(us.get("mode")))
        check("非终态判定", us["judged"] == "IN_PROGRESS", us["judged"])


def test_breaker_trips():
    print("\n[4] 连续连接类失败 → CRITICAL / FM-05")
    with tempfile.TemporaryDirectory() as tmp:
        calls = [{"ok": True, "stage": "creative_plan", "seconds": 20}]
        calls += [{"ok": False, "error": "cannot reach http://x: connection refused"}
                  for _ in range(7)]
        node = make_node(tmp, "t_brk", [
            {"unit_id": "u0", "status": "failed", "error": "connection refused"},
            {"unit_id": "u1", "status": "pending"},
        ], llm_calls=calls)
        r = dg.diagnose(node, None)
        bk = find(r["checks"], "breaker", "t_brk")
        check("识别为 CRITICAL", bk["level"] == "CRITICAL", bk["level"])
        check("指向 FM-05", bk.get("mode") == "FM-05", str(bk.get("mode")))
        check("报告连续数", "连续 7" in bk["detail"], bk["detail"])


def test_breaker_not_tripped_on_partial():
    print("\n[5] 部分恢复不算熔断（严格连续语义）")
    with tempfile.TemporaryDirectory() as tmp:
        calls = [{"ok": False, "error": "connection refused"} for _ in range(5)]
        calls += [{"ok": True, "stage": "draft", "seconds": 30}]
        calls += [{"ok": False, "error": "HTTP 400 bad request"}]
        node = make_node(tmp, "t_pb", [{"unit_id": "u0", "status": "pending"}],
                         llm_calls=calls)
        r = dg.diagnose(node, None)
        bk = find(r["checks"], "breaker", "t_pb")
        check("未触发熔断", bk["level"] in ("OK", "WARN"), bk["level"])
        check("非 FM-05", bk.get("mode") != "FM-05")


def test_missing_artifacts_detected():
    print("\n[6] done 但缺产物 → CRITICAL / FM-07")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_art", [
            {"unit_id": "u0", "status": "done", "work_id": "work_00000001"},
            {"unit_id": "u1", "status": "done", "work_id": "work_00000002"},
        ], with_artifacts=False)
        r = dg.diagnose(node, None)
        art = find(r["checks"], "artifacts", "t_art")
        check("识别缺产物", art["level"] == "CRITICAL", art["level"])
        check("指向 FM-07", art.get("mode") == "FM-07")
        check("列出缺失单元", "u0" in art["detail"] or "u1" in art["detail"])


def test_completed_with_failures_not_faked():
    print("\n[7] 有失败不得冒充完成（FM-07）")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_cwf", [
            {"unit_id": f"u{i}", "status": "done", "work_id": f"work_{i:08d}"}
            for i in range(8)] + [
            {"unit_id": "u8", "status": "failed", "error": "HTTP 400"},
            {"unit_id": "u9", "status": "failed", "error": "HTTP 400"},
        ])
        r = dg.diagnose(node, None)
        us = find(r["checks"], "unit_states", "t_cwf")
        check("判定 COMPLETED_WITH_FAILURES", us["judged"] == "COMPLETED_WITH_FAILURES",
              us["judged"])
        check("不是 COMPLETED", us["judged"] != "COMPLETED")
        check("failed 计数可见", us["counts"]["failed"] == 2)


def test_failed_with_results_when_low_success():
    print("\n[8] 成功率过低 → FAILED_WITH_RESULTS")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_fwr", [
            {"unit_id": "u0", "status": "done", "work_id": "work_00000001"},
            {"unit_id": "u1", "status": "done", "work_id": "work_00000002"},
        ] + [{"unit_id": f"u{i}", "status": "failed", "error": "HTTP 400"}
             for i in range(2, 10)])
        r = dg.diagnose(node, None)
        us = find(r["checks"], "unit_states", "t_fwr")
        check("判定 FAILED_WITH_RESULTS", us["judged"] == "FAILED_WITH_RESULTS",
              us["judged"])


def test_missing_state_is_unknown_not_ok():
    print("\n[9] state 缺失 → UNKNOWN（不谎报健康）")
    with tempfile.TemporaryDirectory() as tmp:
        node = Path(tmp)
        (node / "experiments" / "multi_worker_generation").mkdir(parents=True)
        (node / "experiments" / "multi_worker_generation" / "run.py").write_text("# d\n")
        rd = node / "data" / "multi_worker_generation" / "runs" / "multi_worker_t_ns"
        (rd / "mw_pilot").mkdir(parents=True)
        r = dg.diagnose(node, None)
        us = find(r["checks"], "unit_states", "t_ns")
        check("级别 UNKNOWN", us["level"] == "UNKNOWN", us["level"])
        check("指向 FM-10", us.get("mode") == "FM-10")


def test_memory_gate_levels():
    print("\n[10] 内存门禁分级")
    cases = [
        ({"commit_pct": 50.0, "commit_headroom_gb": 20.0, "avail_phys_gb": 16.0}, "OK"),
        ({"commit_pct": 91.0, "commit_headroom_gb": 8.0, "avail_phys_gb": 4.0}, "CAUTION"),
        ({"commit_pct": 80.0, "commit_headroom_gb": 4.0, "avail_phys_gb": 4.0}, "BLOCK"),
        ({"commit_pct": 95.0, "commit_headroom_gb": 1.0, "avail_phys_gb": 1.0}, "CRITICAL"),
        ({"commit_pct": 70.0, "commit_headroom_gb": 10.0, "avail_phys_gb": 0.5}, "CRITICAL"),
    ]
    for mem, expect in cases:
        os.environ["LIR_FAKE_MEMORY_JSON"] = json.dumps(mem)
        try:
            got = dg.check_memory()["level"]
        finally:
            os.environ.pop("LIR_FAKE_MEMORY_JSON", None)
        check(f"commit {mem['commit_pct']}% headroom {mem['commit_headroom_gb']}GB "
              f"avail {mem['avail_phys_gb']}GB → {expect}", got == expect, f"got={got}")


def test_unknown_does_not_lower_verdict():
    print("\n[11] UNKNOWN 不拉低整体结论（证据不足 != 故障）")
    with tempfile.TemporaryDirectory() as tmp:
        node = make_node(tmp, "t_unk", [
            {"unit_id": "u0", "status": "done", "work_id": "work_00000001"}])
        # 无 llm_calls.jsonl → breaker 为 UNKNOWN
        r = dg.diagnose(node, None)
        os.environ["LIR_FAKE_MEMORY_JSON"] = json.dumps(
            {"commit_pct": 50.0, "commit_headroom_gb": 20.0, "avail_phys_gb": 16.0})
        try:
            r2 = dg.diagnose(node, None)
        finally:
            os.environ.pop("LIR_FAKE_MEMORY_JSON", None)
        known = [c for c in r2["checks"] if c["level"] != "UNKNOWN"]
        check("存在 UNKNOWN 项", any(c["level"] == "UNKNOWN" for c in r2["checks"]))
        check("已知项全 OK", all(c["level"] == "OK" for c in known),
              str([(c["id"], c["level"]) for c in known if c["level"] != "OK"]))


def test_failure_mode_catalog_complete():
    print("\n[12] 故障模式目录完整性（FM-01..FM-12）")
    for i in range(1, 13):
        key = f"FM-{i:02d}"
        fm = dg.FAILURE_MODES.get(key)
        check(f"{key} 存在且字段完整",
              bool(fm) and all(k in fm for k in ("name", "symptoms", "judge", "action")))


def main() -> int:
    print("=" * 62)
    print("  事故诊断器测试")
    print("=" * 62)
    for fn in (test_healthy, test_memory_error_detected, test_stale_claimed_detected,
               test_breaker_trips, test_breaker_not_tripped_on_partial,
               test_missing_artifacts_detected, test_completed_with_failures_not_faked,
               test_failed_with_results_when_low_success,
               test_missing_state_is_unknown_not_ok, test_memory_gate_levels,
               test_unknown_does_not_lower_verdict, test_failure_mode_catalog_complete):
        fn()
    print("\n" + "=" * 62)
    print(f"  汇总：{len(PASS)} 通过 / {len(FAIL)} 失败 / 共 {len(PASS) + len(FAIL)} 项")
    print("=" * 62)
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
