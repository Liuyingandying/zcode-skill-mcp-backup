#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资源门禁：启动/扩容前的 commit/物理内存检查。

门禁（与 production_node/bootstrap.ps1、pilot-100.ps1 同源）：
  commit headroom < 6GB   → BLOCK   禁止新增生产线
  commit >= 90%           → CAUTION 不启动新 worker
  commit >= 92% 或可用物理 < 1024MB → CRITICAL 只停不启（key_2001 语义）

用法：
  python resource_gate.py                 # 人类可读
  python resource_gate.py --json          # 机器可读
  python resource_gate.py --min-headroom-gb 8
退出码：0=OK，1=CAUTION，2=CRITICAL/BLOCK
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nff_common import evaluate_gate, query_memory, reconfigure_stdio  # noqa: E402


def main() -> int:
    reconfigure_stdio()
    ap = argparse.ArgumentParser(description="night-fiction-factory 资源门禁")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--min-headroom-gb", type=float, default=6.0)
    ap.add_argument("--no-new-commit-pct", type=float, default=90.0)
    ap.add_argument("--stop-commit-pct", type=float, default=92.0)
    ap.add_argument("--min-avail-mb", type=float, default=1024.0)
    args = ap.parse_args()

    try:
        mem = query_memory()
    except OSError as e:
        if args.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"[gate] 无法查询内存：{e}")
        return 2

    gate = evaluate_gate(mem, min_headroom_gb=args.min_headroom_gb,
                         no_new_pct=args.no_new_commit_pct,
                         stop_pct=args.stop_commit_pct,
                         min_avail_mb=args.min_avail_mb)
    if args.json:
        print(json.dumps(gate, ensure_ascii=False, indent=2))
    else:
        m = gate["memory"]
        print(f"物理内存：{m['avail_phys_gb']}/{m['total_phys_gb']} GB 可用"
              f"（负载 {m['mem_load_pct']}%）")
        print(f"Commit：{m['commit_used_gb']}/{m['commit_limit_gb']} GB"
              f"（{m['commit_pct']}%，headroom {m['commit_headroom_gb']} GB）")
        print(f"门禁判定：{gate['level']}"
              f"（allow_new_line={gate['allow_new_line']}, stop_running={gate['stop_running']}）")
        for r in gate["reasons"]:
            print(f"  - {r}")
        if gate["level"] == "OK":
            print("  - 通过：可以新增生产线 / worker")
    return {"OK": 0, "CAUTION": 1}.get(gate["level"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
