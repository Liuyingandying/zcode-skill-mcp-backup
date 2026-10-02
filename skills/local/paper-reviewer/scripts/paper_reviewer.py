# -*- coding: utf-8 -*-
"""paper-reviewer v0.1 —— 论文语义质量审查（六模块 + 原子扣分制）
约束：不修改 fixer（子进程委托）；全部检查输出证据位置（quote+行号）；只报告不修复。
输出：paper_review_report.json / PAPER_REVIEW.md / review_trace.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SKILL = Path(__file__).parent
FIXER = Path(__file__).parent.parent / "paper-pipeline-fixer" / "scripts" / "build_paper.py"
KB = Path(__file__).parent.parent.parent / "matical model" / "knowledge_base"
BRIEF = KB / "kb_review_brief.py"

CHECKS = []          # 全部原子检查记录


def add(module, cid, name, status, evidence, deduction=0):
    CHECKS.append({"module": module, "id": cid, "name": name, "status": status,
                   "deduction": deduction if status != "PASS" else 0,
                   "evidence": evidence})
    return status


def line_of(tex: str, needle: str, start: int = 0) -> int:
    p = tex.find(needle, start)
    if p < 0:
        return -1
    return tex.count("\n", 0, p) + 1


# ---------------- M1 结构与章节完整性 ----------------
RULES_CUMCM = [
    ("摘要", [r"\\abstractcn", r"摘\s*要"], True, 3),
    ("问题重述", [r"问题重述", r"问题重述"], True, 3),
    ("模型假设", [r"模型假设", r"基本假设", r"假设"], True, 3),
    ("符号说明", [r"符号说明", r"符号"], True, 2),
    ("建模与求解", [r"模型建立", r"建模", r"问题一", r"问题1", r"问题 1", r"求解"], True, 3),
    ("灵敏度/检验", [r"灵敏度", r"敏感性", r"稳定性", r"检验"], True, 2),
    ("模型评价", [r"评价", r"优缺点", r"讨论"], True, 2),
    ("参考文献", [r"参考文献", r"thebibliography"], True, 2),
    ("附录", [r"附录"], False, 1),
]
RULES_MCM = [
    ("Summary Sheet", [r"Summary Sheet", r"abstractcn", r"摘要"], True, 3),
    ("Introduction", [r"Introduction", r"问题重述", r"Background"], True, 2),
    ("Assumptions", [r"Assumption", r"假设"], True, 2),
    ("Model", [r"Model", r"模型", r"Problem [123]"], True, 3),
    ("Sensitivity", [r"Sensitivity", r"灵敏度"], True, 2),
    ("Strengths & Limitations", [r"Strength", r"Limitation", r"优缺点", r"评价"], True, 2),
    ("References", [r"References", r"thebibliography", r"参考文献"], True, 2),
    ("Memorandum", [r"Memorandum", r"备忘"], False, 1),
]


def m1_structure(tex, competition):
    rules = RULES_MCM if competition == "mcm" else RULES_CUMCM
    # v0.1 修复: 只搜正文（\begin{document} 之后），防止前导区注释/定义污染命中
    marker = chr(92) + "begin{document}"
    body = tex.split(marker, 1)[-1] if marker in tex else tex
    sections = [m.group(1).strip() for m in re.finditer(r"\\section\*?\{([^}]*)\}", body)]
    if not sections:  # 兼容 \input 结构
        sections = [m.group(1) for m in re.finditer(r"\\(?:sub)?section\{([^}]*)\}", body)]
    n_found = 0
    for name, pats, required, ded in rules:
        hit = next((re.search(p, s, re.I) for s in sections for p in pats if re.search(p, s, re.I)), None)
        hit_tex = any(re.search(p, body, re.I) for p in pats)
        if hit or hit_tex:
            if name in ("Summary Sheet", "Memorandum"):
                continue
            n_found += 1
            add("M1", f"M1-{name}", f"章节[{name}]存在", "PASS",
                {"evidence": sections[:12] if name == "建模与求解" else f"命中: {hit.string if hit else 'tex'}"})
        elif required:
            add("M1", f"M1-{name}", f"章节[{name}]缺失", "FAIL",
                {"evidence": f"sections={sections[:12]}"}, deduction=ded)
        else:
            add("M1", f"M1-{name}", f"可选项[{name}]缺失", "WARN", {"evidence": "optional"}, deduction=1)
    # 章节覆盖率 vs O奖骨架（sp-mcm-o-structure: Introduction/Model 100% 低位线）
    cov = n_found / 7
    if cov < 0.85:
        add("M1", "M1-coverage", f"章节覆盖率 {cov:.0%} 低于 85% 警戒线", "WARN", {"evidence": f"{n_found}/7"}, deduction=1)
    return sections


# ---------------- M2 数值溯源（委托 fixer） ----------------
def m2_numeric(paper_dir: Path, results_dir: Path, tex: str):
    out_json = paper_dir / "main.tex.check.json"
    r = subprocess.run([sys.executable, str(FIXER), "check", "--paper", str(paper_dir / "main.tex"),
                        "--results-dir", str(results_dir), "--figures-dir", str(paper_dir.parent / "50_results" / "figures"),
                        "--out", str(out_json)], capture_output=True, text=True)
    try:
        rep = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        add("M2", "M2-fixer", "fixer check 未产出报告（委托失败）", "FAIL", {"evidence": str(e)[:120]}, deduction=3)
        return
    gates = rep.get("gates", {})
    fails = {f[0] if isinstance(f, list) else f: None for f in rep.get("fails", [])}
    add("M2", "M2-provenance", "数值溯源门（正文小数∈结果文件）",
        "PASS" if "numeric_provenance" not in fails else "FAIL",
        {"evidence": f"untraced={gates.get('numeric_provenance', {}).get('untraced', [])[:8]}"}, deduction=0)
    if "numeric_provenance" in fails:
        add("M2", "M2-provenance-fail", "存在无法溯源的正文数值", "FAIL",
            {"evidence": str(fails.get("numeric_provenance"))[:200]}, deduction=3)
    for gname in (GATE_TABLE := "table_rows",):
        br = gates.get(gname, {}).get("bad_rows", [])
        if br:
            add("M2", f"M2-{gname}", "表格行尾单反斜杠", "FAIL", {"evidence": str(br)}, deduction=2)
    add("M2", "M2-placeholders", "占位符扫描", "PASS" if not gates.get("placeholders", {}).get("hits") else "FAIL",
        {"evidence": str(gates.get("placeholders", {}).get("hits", []))[:120]})
    add("M2", "M2-shape", "文档形状（唯一 begin/end document）",
        "PASS" if gates.get("document_shape", {}).get("begin_document_count") == 1 else "FAIL",
        {"evidence": str(gates.get("document_shape"))})
    # fixer 未覆盖的补充: 摘要-正文数字一致性放到 M5；此处补compile状态引用
    if Path(paper_dir / "main.pdf").exists():
        add("M2", "M2-pdf", "main.pdf 存在（compile 由 fixer/人工保证）", "PASS", {"evidence": "main.pdf"})


# ---------------- M3 图表规范 ----------------
def m3_figures(tex: str):
    envs = re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", tex, re.S)
    graphics = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
    no_cap = 0
    short_cap = []
    for env in envs:
        cap = re.search(r"\\caption\{([^}]*)\}", env)
        if not cap:
            no_cap += 1
        elif len(cap.group(1).strip()) < 8:
            short_cap.append(cap.group(1)[:30])
    if no_cap:
        add("M3", "M3-caption", f"{no_cap} 个 figure 环境缺 caption", "FAIL", {"evidence": f"count={no_cap}"}, deduction=2)
    else:
        add("M3", "M3-caption", f"{len(envs)} 个 figure 均有 caption", "PASS", {"evidence": f"n={len(envs)}"})
    if short_cap:
        add("M3", "M3-caption-short", "caption 过短（<8 字符）", "WARN", {"evidence": short_cap}, deduction=1)
    # 解读句: figure 环境之后 300 字符内含分析动词
    weak = []
    for m in re.finditer(r"\\end\{figure\}", tex):
        tail = tex[m.end(): m.end() + 400]
        if not re.search(r"表明|可见|说明|分析|解读|揭示", tail):
            weak.append(line_of(tex, "", m.end()))
    if weak:
        add("M3", "M3-interpretation", f"{len(weak)} 处图后缺机理解读句（2-4 句规范）", "WARN",
            {"evidence": f"lines={weak}"}, deduction=1)
    else:
        add("M3", "M3-interpretation", "各图后均有解读语句", "PASS", {"evidence": f"n_graphics={len(graphics)}"})


# ---------------- M4 学术文本质量门 ----------------
CONNECTIVES = ["综上所述", "此外", "进一步", "与此同时", "显然"]
HYPERBOLES = ["显著", "精度高", "优势明显", "高效", "明显提升", "大幅提升", "效果拔群"]
TERM_PAIRS = [("遗传算法", "进化策略"), ("模拟退火", "退火算法"), ("Kaplan-Meier", "KM 估计")]


def m4_text(tex: str):
    body = tex.split("\\begin{document}", 1)[-1] if "\\begin{document}" in tex else tex
    body_nc = "\n".join("" if ln.lstrip().startswith("%") else ln for ln in body.split("\n"))
    sentences = max(1, len(re.findall(r"[。；.!?\n]", body_nc)))
    conn = sum(body_nc.count(w) for w in CONNECTIVES)
    density = conn / sentences
    tier = ("PASS" if density < 0.15 else "WARN" if density < 0.25 else "FAIL")
    add("M4", "M4-connectives", f"连接词密度 {density:.1%}（{conn}/{sentences} 句）", tier,
        {"evidence": f"thresholds <15/15-25/>25"}, deduction=2 if tier == "FAIL" else 1 if tier == "WARN" else 0)

    # 无数据拔高词
    unsupported = []
    for w in HYPERBOLES:
        for m in re.finditer(w, body_nc):
            window = body_nc[m.start(): m.end() + 60]
            if not re.search(r"\d", window):
                ctx_line = line_of(body_nc, "", m.start())
                unsupported.append({"word": w, "line": ctx_line, "ctx": body_nc[max(0, m.start() - 20): m.end() + 40]})
    add("M4", "M4-hyperbole", f"无数据拔高词 {len(unsupported)} 处（阈值≤3）",
        "PASS" if len(unsupported) <= 3 else "FAIL",
        {"evidence": str(unsupported[:4])}, deduction=2 if len(unsupported) > 3 else 0)

    # 引文结构（v0.1 修复: 兼容 \begin{thebibliography}{9} 可选参数）
    refs = re.search(r"\\begin\{thebibliography\}\s*(?:\{\d*\})?\s*(.*?)\\end\{thebibliography\}", body_nc, re.S)
    if refs:
        entries = re.findall(r"\\bibitem\{[^}]+\}", refs.group(1))
        add("M4", "M4-refs", f"参考文献条目 {len(entries)}", "PASS" if len(entries) >= 5 else "WARN",
            {"evidence": f"count={len(entries)}"}, deduction=1 if len(entries) < 5 else 0)
    else:
        add("M4", "M4-refs", "未找到 thebibliography 引文区", "WARN", {"evidence": "-"}, deduction=1)

    # 摘要数字 ⊆ 正文数字（参数一致性代理）
    abs_m = re.search(r"\\abstractcn\{(.*?)\}\{", body_nc, re.S)
    if abs_m:
        abs_nums = set(re.findall(r"(?<![\d.])(\d+\.\d+)(?!\d)", abs_m.group(1)))
        body_nums = set(re.findall(r"(?<![\d.])(\d+\.\d+)(?!\d)", body_nc))
        missing = sorted(n for n in abs_nums if n not in body_nums)
        add("M4", "M4-abstract-nums", "摘要数字均在正文出现",
            "PASS" if not missing else "FAIL", {"evidence": f"missing={missing[:8]}"}, deduction=2 if missing else 0)

    # 术语统一
    for a, b in TERM_PAIRS:
        if re.search(a, body_nc) and re.search(b, body_nc):
            add("M4", "M4-terms", f"术语疑似混用: {a} / {b}", "WARN",
                {"evidence": f"both '{a}' and '{b}' present"}, deduction=1)


# ---------------- M5 摘要 ----------------
def m5_abstract(tex: str, results_text: str):
    # v0.1 修复: 只搜正文, 跳过前导区的注释/定义文本
    marker = chr(92) + "begin{document}"
    body = tex.split(marker, 1)[-1] if marker in tex else tex
    m = re.search(r"\\abstractcn\{(.*?)\}\s*\n?\s*\{(.*?)\}", body, re.S)
    if not m:
        add("M5", "M5-exists", "未找到摘要（\\abstractcn）", "FAIL", {"evidence": "-"}, deduction=3)
        return
    abstract, keywords = m.group(1), m.group(2)
    add("M5", "M5-length", f"摘要长度 {len(abstract)} 字符", "PASS" if len(abstract) <= 1600 else "WARN",
        {"evidence": f"len={len(abstract)}"}, deduction=1 if len(abstract) > 1600 else 0)
    nums = re.findall(r"(?<![\d.])(\d+\.\d+)(?!\d)", abstract)
    add("M5", "M5-keynums", f"摘要关键数值 {len(nums)} 个（要求 ≥3）",
        "PASS" if len(nums) >= 3 else "FAIL", {"evidence": str(nums[:8])}, deduction=2 if len(nums) < 3 else 0)
    src_nums = set(re.findall(r"(?<![\d.])(\d+\.\d+)(?!\d)", results_text))
    missing = [n for n in nums if n not in src_nums]
    add("M5", "M5-nums-provenance", "摘要数值可溯源到结果文件",
        "PASS" if not missing else "FAIL", {"evidence": f"missing={missing[:8]}"}, deduction=3 if missing else 0)
    has_kw = len(keywords.strip()) > 4
    add("M5", "M5-keywords", "关键词存在", "PASS" if has_kw else "WARN", {"evidence": keywords[:60]}, deduction=1 if not has_kw else 0)
    has_method = bool(re.search(r"建立|模型|方法|提出", abstract))
    has_result = bool(re.search(r"结果|得到|求解|收敛|准确|误差", abstract))
    add("M5", "M5-structure", "三段式要素（方法表述+结果表述）",
        "PASS" if (has_method and has_result) else "WARN", {"evidence": f"method={has_method} result={has_result}"},
        deduction=1 if not (has_method and has_result) else 0)


# ---------------- M6 领域风险对照（KB 简报） ----------------
AUTO_RULES = {
    "评价决策": [("组合赋权 CR/一致性检验", r"一致性|CR\b|一致性检验"), ("权重敏感性分析", r"敏感")],
    "预测": [("基线/对照模型", r"基线|对照|朴素"), ("验证划分声明", r"验证|划分|交叉")],
    "机理建模": [("量纲/稳定性声明", r"量纲|稳定性|收敛"), ("残差诊断", r"残差")],
    "优化": [("可行解先于最优", r"可行"), ("约束完整性", r"约束")],
}


def m6_domain(problem_type: str, tex: str, out_dir: Path):
    brief_out = out_dir / "kb_brief.md"
    r = subprocess.run([sys.executable, str(BRIEF), "--problem-type", problem_type,
                        "--out", str(brief_out)], capture_output=True, text=True)
    lines = brief_out.read_text(encoding="utf-8").split("\n") if brief_out.exists() else []
    manual, auto_pass, auto_flag = [], 0, 0
    # 自动规则
    for name, pat in AUTO_RULES.get(problem_type, []):
        hit = bool(re.search(pat, tex))
        if hit:
            auto_pass += 1
            add("M6", f"M6-auto-{name}", f"领域检查[{name}]", "PASS", {"evidence": f"tex 含 {pat}"})
        else:
            auto_flag += 1
            add("M6", f"M6-auto-{name}", f"领域检查[{name}]未在论文中定位", "FLAG",
                {"evidence": f"pattern={pat}"}, deduction=1)
    # 简报人工对照清单（不扣分, 列为 manual）
    card = None
    for ln in lines:
        if ln.startswith("### "):
            card = ln[4:].strip()
        elif "review 检查项" in ln:
            manual.append({"card": card, "check": ln.split("review 检查项:")[-1].strip(" -")})
    return auto_pass, auto_flag, manual


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-dir", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--problem-type", default="机理建模")
    ap.add_argument("--competition", default="cumcm", choices=["cumcm", "mcm"])
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()

    paper_dir = Path(a.paper_dir)
    results_dir = Path(a.results_dir)
    out_dir = Path(a.out_dir) if a.out_dir else paper_dir / "_review"
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_p = paper_dir / "main.tex"
    tex = tex_p.read_text(encoding="utf-8")

    m1_structure(tex, a.competition)
    m2_numeric(paper_dir, results_dir, tex)
    m3_figures(tex)
    m4_text(tex)
    m5_abstract(tex, _results_text(results_dir))
    auto_pass, auto_flag, manual = m6_domain(a.problem_type, tex, out_dir)

    total = max(0, 100 - sum(c["deduction"] for c in CHECKS))
    verdict = ("提交就绪" if total >= 90 else "需修改" if total >= 75 else "返工" if total >= 60 else "退回")
    code = 0 if total >= 90 else 1 if total >= 75 else 2 if total >= 60 else 3

    report = {"paper": str(paper_dir), "competition": a.competition, "problem_type": a.problem_type,
              "generated": datetime.now().strftime("%F %T"),
              "total": total, "verdict": verdict, "exit_code": code,
              "checks": CHECKS,
              "m6_manual_checklist": manual,
              "m6_auto": {"pass": auto_pass, "flag": auto_flag}}
    (out_dir / "paper_review_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    trace = {"run": str(paper_dir), "executed_at": datetime.now().strftime("%F %T"),
             "frozen_checklist": "v0.1 (M1×9 / M2×6 / M3×3 / M4×6 / M5×5 / M6 auto+manual)",
             "fixer_gate_json": str(out_json_name()), "kb_brief": str(out_dir / "kb_brief.md"),
             "checks": CHECKS, "total": total, "verdict": verdict}
    (out_dir / "review_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# PAPER_REVIEW —— {paper_dir.name} ({a.competition}/{a.problem_type})",
          f"总分 **{total}** ｜ 判定 **{verdict}** ｜ 扣分明细:", ""]
    for c in CHECKS:
        if c["status"] != "PASS":
            md.append(f"- [{c['status']} -{c['deduction']}] {c['module']} {c['name']} → {str(c['evidence'])[:120]}")
    md += ["", f"通过项 {sum(1 for c in CHECKS if c['status'] == 'PASS')}/{len(CHECKS)}。"
           if any(c["status"] != "PASS" for c in CHECKS) else "全部检查 PASS。",
           "", "## M6 人工对照清单", ""]
    for m in manual:
        md.append(f"- [{m['card']}] {m['check'][:150]}")
    (out_dir / "PAPER_REVIEW.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[paper-reviewer] total={total} verdict={verdict} checks={len(CHECKS)} -> {out_dir}")
    sys.exit(code)


def out_json_name():
    return "main.tex.check.json"


def _results_text(rd: Path) -> str:
    buf = ""
    for p in sorted(Path(rd).rglob("*")):
        if p.suffix.lower() in (".md", ".csv", ".json", ".txt") and p.is_file():
            buf += p.read_text(encoding="utf-8", errors="ignore")
    return buf


if __name__ == "__main__":
    main()
