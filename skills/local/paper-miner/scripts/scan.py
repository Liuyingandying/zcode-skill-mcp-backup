# -*- coding: utf-8 -*-
"""scan.py —— 论文库清点: 年份/题号/O奖过滤, 输出 inventory.json
id 规则: pp-<year><letter小写>-<控制号>  (如 pp-2023a-2300336)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

YEAR_DIRS = {2023: "2023年美赛O奖论文", 2024: "2024年美赛O奖论文", 2025: "2025美赛O奖论文"}
LETTER_RE = re.compile(r"(?:^|[\\/])(?:2023年美国大学生数学建模竞赛（常规赛）O奖论文|202[3-5]年?美赛[A-F]题O奖论文|[A-F])(?:[\\/]|$)")


def letter_of(path: Path, year_root: Path) -> str | None:
    rel = path.parent.relative_to(year_root)
    parts = [p for p in rel.parts]
    for p in parts:
        m = re.search(r"[（(]?[A-F]题[)）]?$|^([A-F])$", p.strip())
        if m:
            return m.group(1) or m.group(0)[0]
        m2 = re.match(r"^([A-F])$", p.strip())
        if m2:
            return m2.group(1)
    # 兜底: 目录名含单个字母结尾如 "2024年美赛A题O奖论文"
    for p in parts:
        m = re.search(r"美赛([A-F])题", p)
        if m:
            return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:/BaiduNetdiskDownload/【4】美赛特等奖优秀论文集")
    ap.add_argument("--years", default="2023,2024,2025")
    ap.add_argument("--out", default="inventory.json")
    a = ap.parse_args()
    root = Path(a.root)
    papers = []
    for y in [int(x) for x in a.years.split(",")]:
        yroot = root / YEAR_DIRS[y]
        if not yroot.exists():
            print(f"[scan][WARN] 缺目录: {yroot}")
            continue
        for pdf in sorted(yroot.rglob("*.pdf")):
            m = re.match(r"(\d{2})\d{4,}\.pdf$", pdf.name)
            letter = letter_of(pdf, yroot)
            if not letter:
                continue
            papers.append({
                "id": f"pp-{y}{letter.lower()}-{pdf.stem}",
                "year": y, "letter": letter, "file": str(pdf),
                "bytes": pdf.stat().st_size,
            })
    inv = {"generated": datetime.now().strftime("%F %T"), "root": str(root),
           "years": a.years, "count": len(papers), "papers": papers}
    Path(a.out).write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    dist = Counter((p["year"], p["letter"]) for p in papers)
    print(f"[scan] {len(papers)} 篇: " + ", ".join(f"{y}{l}×{c}" for (y, l), c in sorted(dist.items())))
    print(f"[scan] inventory -> {a.out}")


if __name__ == "__main__":
    main()
