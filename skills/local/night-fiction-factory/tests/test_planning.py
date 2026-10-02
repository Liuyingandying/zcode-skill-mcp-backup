# -*- coding: utf-8 -*-
"""规划与预算测试：4 线规划 / tag 唯一 / worker 预算 / commit 不足阻止扩容 / 计划校验。"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
import nff_common as nff  # noqa: E402
from plan_night import build_plan, validate_plan  # noqa: E402


def mem(avail_gb, commit_pct=60.0):
    return {"commit_avail_gb": avail_gb, "commit_headroom_gb": avail_gb,
            "commit_used_gb": 100 - avail_gb, "commit_limit_gb": 100,
            "commit_pct": commit_pct, "avail_phys_gb": avail_gb,
            "total_phys_gb": 32, "mem_load_pct": 50}


class TestBuildPlan(unittest.TestCase):
    def opts(self, **kw):
        base = dict(lines=4, genres="科幻,悬疑,都市,奇幻", total=800, targets=None,
                    stop_at="08:00", provider="glm", model="", start_mode="now",
                    max_total_workers=12, per_line_cap=9, plan_id=None,
                    _node_root=None, memory=mem(20))
        base.update(kw)
        return base

    def test_four_lines_targets_split(self):
        plan, warnings = build_plan(self.opts())
        self.assertEqual(len(plan["lines"]), 4)
        self.assertEqual(sum(l["target"] for l in plan["lines"].values()), 800)
        self.assertEqual(plan["genre_mode"], "label_only")
        self.assertEqual(len(warnings), 0)

    def test_tags_unique_and_valid(self):
        plan, _ = build_plan(self.opts())
        tags = [l["tag"] for l in plan["lines"].values()]
        self.assertEqual(len(tags), len(set(tags)))
        for t in tags:
            self.assertTrue(nff.TAG_RE.match(t), t)
        # 日期前缀 + 中文题材正确映射为英文 slug
        self.assertTrue(tags[0].startswith("night_"))
        self.assertIn("scifi", tags[0])
        self.assertIn("mystery", tags[1])

    def test_chinese_genre_slug_mapping_and_hash_fallback(self):
        self.assertEqual(nff.sanitize_slug("科幻"), "scifi")
        slug = nff.sanitize_slug("赛博朋克")
        self.assertTrue(slug.startswith("g") and len(slug) == 7)
        self.assertEqual(slug, nff.sanitize_slug("赛博朋克"))

    def test_targets_explicit(self):
        plan, _ = build_plan(self.opts(lines=3, genres="科幻,悬疑,都市",
                                       total=None, targets="200,200,100"))
        self.assertEqual([l["target"] for l in plan["lines"].values()],
                         [200, 200, 100])

    def test_genre_cycle_when_fewer(self):
        plan, warnings = build_plan(self.opts(lines=4, genres="科幻,悬疑"))
        self.assertEqual(len(plan["lines"]), 4)
        self.assertTrue(any("循环编号" in w for w in warnings))

    def test_worker_budget_round_robin(self):
        plan, _ = build_plan(self.opts())
        ws = [l["workers"] for l in plan["lines"].values()]
        self.assertEqual(sum(ws), 12)
        self.assertEqual(ws, [3, 3, 3, 3])

    def test_commit_shortfall_blocks_workers(self):
        # commit avail 2.5GB → mem_cap = (2.5-2)*8 = 4 → 4 线各 1，尚可跑
        plan, _ = build_plan(self.opts(memory=mem(2.5)))
        ws = [l["workers"] for l in plan["lines"].values()]
        self.assertEqual(sum(ws), 4)
        # commit avail 1.0GB → cap=0 → 全部 0，警告待扩容
        plan2, warn2 = build_plan(self.opts(memory=mem(1.0)))
        self.assertTrue(all(l["workers"] == 0 for l in plan2["lines"].values()))
        self.assertTrue(any("PLANNED 待扩容" in w for w in warn2))


class TestAllocateWorkers(unittest.TestCase):
    def test_six_lines_budget_twelve(self):
        alloc, budget = nff.allocate_workers(6, 12, memory=None)
        self.assertEqual(alloc, [2, 2, 2, 2, 2, 2])
        self.assertEqual(budget, 12)

    def test_memory_shrinks_budget(self):
        alloc, budget = nff.allocate_workers(6, 12, memory=mem(2.5))
        self.assertEqual(budget, 4)
        self.assertEqual(sum(a == 0 for a in alloc), 2)  # 2 条线保持 PLANNED

    def test_per_line_cap_engine_limit(self):
        alloc, _ = nff.allocate_workers(2, 12, memory=None, per_line_cap=9)
        self.assertEqual(alloc, [6, 6])
        alloc2, _ = nff.allocate_workers(1, 20, memory=None, per_line_cap=9)
        self.assertEqual(alloc2, [9])


class TestGate(unittest.TestCase):
    def test_ok(self):
        g = nff.evaluate_gate(mem(20))
        self.assertEqual(g["level"], "OK")
        self.assertTrue(g["allow_new_line"])
        self.assertFalse(g["stop_running"])

    def test_headroom_below_6gb_blocks_new_line(self):
        g = nff.evaluate_gate(mem(4.0, commit_pct=80))
        self.assertEqual(g["level"], "BLOCK")
        self.assertFalse(g["allow_new_line"])

    def test_commit_90_no_new_worker(self):
        g = nff.evaluate_gate({"commit_headroom_gb": 8.0, "commit_pct": 90.5,
                               "avail_phys_gb": 4.0, "commit_avail_gb": 8.0,
                               "commit_used_gb": 29, "commit_limit_gb": 32})
        self.assertEqual(g["level"], "CAUTION")
        self.assertFalse(g["allow_new_line"])
        self.assertFalse(g["stop_running"])

    def test_commit_92_stop_only(self):
        g = nff.evaluate_gate({"commit_headroom_gb": 2.0, "commit_pct": 93.0,
                               "avail_phys_gb": 2.0, "commit_avail_gb": 2.0,
                               "commit_used_gb": 30, "commit_limit_gb": 32})
        self.assertEqual(g["level"], "CRITICAL")
        self.assertTrue(g["stop_running"])
        self.assertFalse(g["allow_new_line"])

    def test_low_avail_phys_is_critical(self):
        g = nff.evaluate_gate({"commit_headroom_gb": 10.0, "commit_pct": 70.0,
                               "avail_phys_gb": 0.5, "commit_avail_gb": 10.0,
                               "commit_used_gb": 20, "commit_limit_gb": 32})
        self.assertEqual(g["level"], "CRITICAL")


class TestValidatePlan(unittest.TestCase):
    def base_plan(self):
        plan, _ = build_plan(dict(
            lines=2, genres="科幻,悬疑", total=400, targets=None, stop_at="08:00",
            provider="glm", model="", start_mode="now", max_total_workers=12,
            per_line_cap=9, plan_id="t", _node_root=None, memory=mem(20)))
        return plan

    def test_valid_plan_passes(self):
        self.assertEqual(validate_plan(self.base_plan()), [])

    def test_too_many_workers_rejected(self):
        plan = self.base_plan()
        for l in plan["lines"].values():
            l["workers"] = 12
        self.assertTrue(any("上限 9" in e for e in validate_plan(plan)))

    def test_duplicate_tag_rejected(self):
        plan = self.base_plan()
        lines = list(plan["lines"].values())
        lines[1]["tag"] = lines[0]["tag"]
        self.assertTrue(any("tag 重复" in e for e in validate_plan(plan)))

    def test_genre_mode_must_be_label_only(self):
        plan = self.base_plan()
        plan["genre_mode"] = "injected"
        self.assertTrue(any("label_only" in e for e in validate_plan(plan)))

    def test_parse_stop_at_future_today(self):
        now = datetime(2026, 9, 27, 7, 0)
        d = nff.parse_stop_at("08:00", now=now)
        self.assertEqual((d.day, d.hour), (27, 8))
        d2 = nff.parse_stop_at("08:00", now=datetime(2026, 9, 27, 9, 0))
        self.assertEqual((d2.day, d2.hour), (28, 8))


if __name__ == "__main__":
    unittest.main()
