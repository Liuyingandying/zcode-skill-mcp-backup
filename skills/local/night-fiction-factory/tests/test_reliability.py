# -*- coding: utf-8 -*-
"""可靠性规则测试：完成判定 / resume 语义 / stale claimed / 产物核对 / state 显式改写。"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
import nff_common as nff  # noqa: E402
from nff_common import (artifact_ok, classify_launch, counts_from_units,  # noqa: E402
                        judge_counts, effective_line_status, rewrite_failed_to_pending,
                        stale_claimed, success_count)


def counts(pending=0, claimed=0, done=0, failed=0, recovered=0):
    return {"pending": pending, "claimed": claimed, "done": done,
            "failed": failed, "recovered_success": recovered, "total":
            pending + claimed + done + failed + recovered}


class TestJudgeCounts(unittest.TestCase):
    def test_completed_requires_all_clear(self):
        self.assertEqual(judge_counts(counts(done=200), 200), "COMPLETED")
        # done 195 + recovered 5 也算成功
        self.assertEqual(judge_counts(counts(done=195, recovered=5), 200), "COMPLETED")

    def test_pending_zero_but_claimed_left_is_not_completed(self):
        self.assertEqual(judge_counts(counts(done=199, claimed=1), 200), "IN_PROGRESS")

    def test_pending_zero_but_failed_left_is_not_completed(self):
        self.assertEqual(judge_counts(counts(done=180, failed=20), 200),
                         "COMPLETED_WITH_FAILURES")

    def test_failed_with_results_below_floor(self):
        self.assertEqual(judge_counts(counts(done=20, failed=180), 200),
                         "FAILED_WITH_RESULTS")

    def test_in_progress(self):
        self.assertEqual(judge_counts(counts(pending=50, done=150), 200), "IN_PROGRESS")

    def test_success_count_merges_recovered(self):
        self.assertEqual(success_count(counts(done=10, recovered=5)), 15)


class TestEffectiveStatus(unittest.TestCase):
    def test_live_wins(self):
        self.assertEqual(effective_line_status("STOPPED", "IN_PROGRESS", 2), "RUNNING")

    def test_final_judged(self):
        self.assertEqual(effective_line_status("RUNNING", "COMPLETED", 0), "COMPLETED")

    def test_registry_paused_kept(self):
        self.assertEqual(effective_line_status("PAUSED_UPSTREAM", "IN_PROGRESS", 0),
                         "PAUSED_UPSTREAM")
        self.assertEqual(effective_line_status("STOPPED", "IN_PROGRESS", 0), "STOPPED")

    def test_planned_never_failed_resumable(self):
        self.assertEqual(effective_line_status("PLANNED", "IN_PROGRESS", 0), "PLANNED")

    def test_running_without_process_is_resumable(self):
        self.assertEqual(effective_line_status("RUNNING", "IN_PROGRESS", 0),
                         "FAILED_RESUMABLE")


class TestClassifyLaunch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rd = Path(self.tmp.name) / "multi_worker_night_t_scifi_01"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_state(self, units):
        (self.rd / "mw_pilot").mkdir(parents=True)
        (self.rd / "mw_pilot" / "state.json").write_text(
            json.dumps({"batch": "mw_pilot", "size": len(units),
                        "units": units, "status": "running"}), encoding="utf-8")

    def test_fresh(self):
        self.assertEqual(classify_launch(self.rd, None, 0, 10), "fresh")

    def test_completed_never_relaunch(self):
        self._write_state([{"unit_id": f"u{i}", "status": "done"} for i in range(10)])
        state = json.loads((self.rd / "mw_pilot" / "state.json").read_text())
        self.assertEqual(classify_launch(self.rd, state, 0, 10), "completed")

    def test_resumable(self):
        self._write_state([{"unit_id": "u0", "status": "done"},
                           {"unit_id": "u1", "status": "pending"}])
        state = json.loads((self.rd / "mw_pilot" / "state.json").read_text())
        self.assertEqual(classify_launch(self.rd, state, 0, 2), "resumable")

    def test_double_launch_refused(self):
        self._write_state([{"unit_id": "u0", "status": "pending"}])
        state = json.loads((self.rd / "mw_pilot" / "state.json").read_text())
        self.assertEqual(classify_launch(self.rd, state, 1, 1), "already_running")

    def test_leftover_dir_without_state_blocked(self):
        self.rd.mkdir(parents=True)
        self.assertEqual(classify_launch(self.rd, None, 0, 10), "block_leftover")


class TestStaleAndArtifact(unittest.TestCase):
    def test_stale_claimed_by_heartbeat_age(self):
        now = time.time()
        units = [{"status": "claimed", "heartbeat": now - 999},
                 {"status": "claimed", "heartbeat": now - 5},
                 {"status": "claimed"},                # heartbeat 缺失 → stale
                 {"status": "done", "heartbeat": now - 999}]
        stales = stale_claimed(units, 120.0, now=now)
        self.assertEqual(len(stales), 2)

    def test_artifact_ok(self):
        tmp = tempfile.TemporaryDirectory()
        rd = Path(tmp.name)
        wdir = rd / "mw_pilot" / "works" / "mw_pilot-scifi-0000"
        wdir.mkdir(parents=True)
        # 1) 缺文件
        self.assertFalse(artifact_ok(rd, "mw_pilot-scifi-0000"))
        # 2) metadata unit_id 不自洽
        (wdir / "content.md").write_text("正文", encoding="utf-8")
        (wdir / "metadata.json").write_text(
            json.dumps({"unit_id": "other", "work_id": "work_00000001"}), encoding="utf-8")
        self.assertFalse(artifact_ok(rd, "mw_pilot-scifi-0000"))
        # 3) 完整
        (wdir / "metadata.json").write_text(
            json.dumps({"unit_id": "mw_pilot-scifi-0000", "work_id": "work_00000001"}),
            encoding="utf-8")
        self.assertTrue(artifact_ok(rd, "mw_pilot-scifi-0000"))
        tmp.cleanup()


class TestExplicitStateRewrite(unittest.TestCase):
    def test_only_failed_flipped(self):
        state = {"units": [
            {"unit_id": "a", "status": "done", "attempts": 1, "work_id": "work_1"},
            {"unit_id": "b", "status": "failed", "attempts": 3, "error": "HTTP 502",
             "worker": "worker_1", "claimed_at": 1.0, "heartbeat": 2.0},
            {"unit_id": "c", "status": "pending", "attempts": 0},
            {"unit_id": "d", "status": "recovered_success", "attempts": 1},
        ]}
        n = rewrite_failed_to_pending(state)
        self.assertEqual(n, 1)
        u = state["units"][1]
        self.assertEqual(u["status"], "pending")
        self.assertEqual(u["attempts"], 0)
        for k in ("worker", "claimed_at", "heartbeat", "error"):
            self.assertNotIn(k, u)
        # done / pending / recovered 不受影响
        self.assertEqual(state["units"][0]["status"], "done")
        self.assertEqual(state["units"][2]["status"], "pending")
        self.assertEqual(state["units"][3]["status"], "recovered_success")

    def test_counts_after_rewrite(self):
        state = {"units": [{"unit_id": "b", "status": "failed", "attempts": 3}]}
        rewrite_failed_to_pending(state)
        c = counts_from_units(state["units"])
        self.assertEqual(c["pending"], 1)
        self.assertEqual(c["failed"], 0)


if __name__ == "__main__":
    unittest.main()
