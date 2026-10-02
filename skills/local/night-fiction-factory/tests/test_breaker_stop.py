# -*- coding: utf-8 -*-
"""熔断 / 安全停止 / PID 隔离 / Key 不泄漏 测试。"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
import nff_common as nff  # noqa: E402
from nff_common import (breaker_from_state, breaker_verdict, build_stop_plan,  # noqa: E402
                        is_connection_error, match_line_pids)

SKILL_ROOT = Path(__file__).resolve().parents[1]
NODE = "d:\\ainode"  # 测试用假 Node 路径


def fake_procs():
    rd1 = str(Path(NODE) / "data/multi_worker_generation/runs/multi_worker_tag_a")
    rd2 = str(Path(NODE) / "data/multi_worker_generation/runs/multi_worker_tag_b")
    return [
        {"pid": 111, "cmd": f"python experiments\\multi_worker_generation\\run.py "
                            f"--limit 200 --workers 2 --tag tag_a"},
        {"pid": 112, "cmd": f"python experiments\\multi_worker_generation\\worker.py "
                            f"--worker-id worker_1 --batch-dir {rd1}\\mw_pilot "
                            f"--run-dir {rd1}"},
        {"pid": 222, "cmd": f"python experiments\\multi_worker_generation\\run.py "
                            f"--limit 200 --workers 2 --tag tag_b"},
        {"pid": 223, "cmd": f"python experiments\\multi_worker_generation\\worker.py "
                            f"--worker-id worker_1 --batch-dir {rd2}\\mw_pilot "
                            f"--run-dir {rd2}"},
        {"pid": 8787, "cmd": "python dashboard\\server.py --port 8787"},      # 无关进程
        {"pid": os.getpid(), "cmd": "python some_other_tool.py"},             # 自身
    ]


def fake_plan():
    rd1 = str(Path(NODE) / "data/multi_worker_generation/runs/multi_worker_tag_a")
    rd2 = str(Path(NODE) / "data/multi_worker_generation/runs/multi_worker_tag_b")
    return {"plan_id": "p", "lines": {
        "a": {"line_id": "a", "tag": "tag_a", "target": 200, "workers": 2,
              "status": "RUNNING", "pid": 111, "run_dir": rd1},
        "b": {"line_id": "b", "tag": "tag_b", "target": 200, "workers": 2,
              "status": "RUNNING", "pid": 222, "run_dir": rd2},
    }}


class TestBreaker(unittest.TestCase):
    def recs(self, *specs):
        # specs: ("ok"|"conn"|"other")，按时间升序
        out = []
        for s in specs:
            if s == "ok":
                out.append({"ok": True})
            elif s == "conn":
                out.append({"ok": False, "error": "cannot reach http://127.0.0.1:8000: "
                                                 "[Errno 10061] connection refused"})
            else:
                out.append({"ok": False, "error": "HTTP 400 validation failed"})
        return out

    def test_connection_error_patterns(self):
        for t in ("cannot reach http://x", "HTTP 502 Bad Gateway", "read timeout",
                  "getaddrinfo failed", "[Errno 10061]"):
            self.assertTrue(is_connection_error(t), t)
        self.assertFalse(is_connection_error("HTTP 400 validation failed"))

    def test_six_consecutive_connection_failures_trip(self):
        v = breaker_verdict(self.recs("ok", "conn", "conn", "conn", "conn",
                                      "conn", "conn"), threshold=6)
        self.assertEqual(v["state"], "OUTAGE")

    def test_success_breaks_streak(self):
        v = breaker_verdict(self.recs("conn", "conn", "conn", "ok",
                                      "conn", "conn", "conn"), threshold=6)
        self.assertEqual(v["state"], "HEALTHY")

    def test_non_connection_failures_do_not_trip(self):
        v = breaker_verdict(self.recs(*(["other"] * 8)), threshold=6)
        self.assertEqual(v["state"], "HEALTHY")

    def test_insufficient_samples_unknown(self):
        v = breaker_verdict(self.recs("conn", "conn"), threshold=6)
        self.assertEqual(v["state"], "UNKNOWN")

    def test_state_fallback(self):
        units = [{"status": "failed", "error": "connection refused"} for _ in range(6)]
        units.append({"status": "done"})
        v = breaker_from_state(units, threshold=6)
        self.assertEqual(v["state"], "OUTAGE")

    def test_match_line_pids_scoped(self):
        procs = fake_procs()
        rd1 = Path(NODE) / "data/multi_worker_generation/runs/multi_worker_tag_a"
        pids = match_line_pids(procs, "tag_a", rd1)
        self.assertEqual(pids, [111, 112])


class TestStopPlan(unittest.TestCase):
    def test_single_line_stop_is_scoped(self):
        r = build_stop_plan(fake_plan(), ["a"], fake_procs())
        killed = sorted(p for k in r["kills"] for p in k["pids"])
        self.assertEqual(killed, [111, 112])
        self.assertTrue(all(k["line_id"] == "a" for k in r["kills"]))

    def test_plan_level_stop(self):
        r = build_stop_plan(fake_plan(), None, fake_procs())
        killed = sorted(p for k in r["kills"] for p in k["pids"])
        self.assertEqual(killed, [111, 112, 222, 223])

    def test_pid_isolation_never_touches_unrelated(self):
        r = build_stop_plan(fake_plan(), None, fake_procs())
        killed = {p for k in r["kills"] for p in k["pids"]}
        self.assertNotIn(8787, killed)            # dashboard
        self.assertNotIn(os.getpid(), killed)     # 自身/其他工具

    def test_pid_reuse_refused(self):
        plan = fake_plan()
        plan["lines"]["b"]["pid"] = 8787           # 登记的 PID 被别的程序复用
        procs = fake_procs()
        # tag_b 的真实进程不在表里 → 只剩复用 PID 这条线索
        procs = [p for p in procs if p["pid"] not in (222, 223)]
        r = build_stop_plan(plan, ["b"], procs)
        self.assertEqual(r["kills"], [])
        self.assertTrue(any("拒绝误杀" in s["reason"] for s in r["skipped"]))

    def test_dead_pid_reported(self):
        plan = fake_plan()
        plan["lines"]["b"]["pid"] = 99999
        procs = [p for p in fake_procs() if p["pid"] not in (222, 223)]
        r = build_stop_plan(plan, ["b"], procs)
        self.assertEqual(r["kills"], [])
        self.assertTrue(any("已不在进程表" in s["reason"] for s in r["skipped"]))

    def test_final_line_skipped(self):
        plan = fake_plan()
        plan["lines"]["a"]["status"] = "COMPLETED"
        r = build_stop_plan(plan, None, fake_procs())
        killed = sorted(p for k in r["kills"] for p in k["pids"])
        self.assertEqual(killed, [222, 223])
        self.assertTrue(any("终态" in s["reason"] for s in r["skipped"]))


class TestNoKeyLeak(unittest.TestCase):
    KEY_PATTERNS = [
        r"sk-[A-Za-z0-9]{16,}",
        r"(?i)api[_-]?key[\"']?\s*[:=]\s*[\"'][A-Za-z0-9+/_\-]{16,}[\"']",
        r"TJULLM_API_KEY_\d[\"']?\s*[:=]\s*[\"'][A-Za-z0-9+/_\-]{8,}[\"']",
    ]

    def test_skill_tree_contains_no_key_values(self):
        import re
        offenders = []
        for root, _dirs, files in os.walk(SKILL_ROOT):
            if "__pycache__" in root:
                continue
            for fn in files:
                if not fn.endswith((".md", ".py", ".json")):
                    continue
                text = (Path(root) / fn).read_text(encoding="utf-8", errors="replace")
                for pat in self.KEY_PATTERNS:
                    if re.search(pat, text):
                        offenders.append(f"{fn}:{pat}")
        self.assertEqual(offenders, [])

    def test_generated_plan_carries_no_credentials(self):
        from plan_night import build_plan
        plan, _ = build_plan(dict(
            lines=2, genres="科幻,悬疑", total=4, targets=None, stop_at="08:00",
            provider="glm", model="", start_mode="now", max_total_workers=4,
            per_line_cap=9, plan_id="leak", _node_root=None, memory={
                "commit_avail_gb": 20, "commit_headroom_gb": 20,
                "commit_used_gb": 10, "commit_limit_gb": 32, "commit_pct": 31.3,
                "avail_phys_gb": 16, "total_phys_gb": 32, "mem_load_pct": 40}))
        blob = json.dumps(plan, ensure_ascii=False)
        for pat in self.KEY_PATTERNS:
            self.assertIsNone(__import__("re").search(pat, blob), pat)
        # provider 只允许 profile 名，不出现任何 URL/Key 值
        self.assertEqual(plan["provider"], "glm")
        self.assertNotIn("apikey", blob.lower())
        self.assertNotIn("bearer", blob.lower())


if __name__ == "__main__":
    unittest.main()
