# -*- coding: utf-8 -*-
"""mine.py —— 文本 -> paper_record.json
客观字段(题型/模型/算法/引用)=词典抽取带证据行; judgment 字段留待 LLM 填写(merge 步骤)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OFFICIAL_TYPE = {"A": "连续(Continuous)", "B": "离散(Discrete)", "C": "数据洞察(Data Insights)",
                 "D": "运筹/网络(OR/Network)", "E": "可持续(Sustainability)", "F": "政策(Policy)"}
KB_CATEGORY = {"A": ["机理建模"], "B": ["优化", "离散模型"], "C": ["数据分析"],
               "D": ["优化", "网络分析"], "E": ["数据分析", "评价决策"], "F": ["评价决策", "政策建模"]}

MODELS = {
    "灰色预测GM(1,1)": [r"GM\s*\(\s*1\s*,\s*1\s*\)", r"grey prediction", r"灰色预测"],
    "层次分析法AHP": [r"\bAHP\b", r"层次分析法", r"analytic hierarchy"],
    "TOPSIS": [r"TOPSIS"],
    "熵权法": [r"entropy weight", r"熵权"],
    "随机森林": [r"random forest"],
    "XGBoost/LightGBM": [r"xgboost", r"lightgbm", r"gradient boosting"],
    "神经网络/深度学习": [r"neural network", r"deep learning", r"\bLSTM\b", r"\bCNN\b", r"\bGRU\b", r"transformer"],
    "逻辑回归": [r"logistic regression", r"logit model"],
    "Logistic增长": [r"logistic (growth|map|model)"],
    "种群动力学": [r"population (dynamics|model|growth|iteration)", r"Leslie", r"Ricker"],
    "线性回归/最小二乘": [r"linear regression", r"\bOLS\b", r"least squares"],
    "时间序列ARIMA": [r"\bARIMA\b", r"autoregressive integrated"],
    "微分方程模型": [r"differential equation", r"\bODE\b", r"\bPDE\b", r"\bSIR\b", r"\bSEIR\b"],
    "蒙特卡洛模拟": [r"Monte Carlo", r"蒙特卡洛"],
    "元胞自动机": [r"cellular automaton", r"cellular automata"],
    "图论/网络模型": [r"graph theory", r"network (model|analysis)", r"\bDijkstra\b", r"shortest path", r"minimum spanning tree"],
    "整数/混合整数规划": [r"integer programming", r"mixed[- ]integer", r"\bMILP\b", r"\bILP\b"],
    "线性规划": [r"linear programming", r"\bLP\b"],
    "遗传算法": [r"genetic algorithm", r"\bGA\b"],
    "模拟退火": [r"simulated annealing"],
    "粒子群优化": [r"particle swarm", r"\bPSO\b"],
    "K-means聚类": [r"[Kk]-means"],
    "层次聚类": [r"hierarchical cluster"],
    "主成分分析PCA": [r"principal component", r"\bPCA\b"],
    "决策树": [r"decision tree"],
    "支持向量机SVM": [r"support vector machine", r"\bSVM\b"],
    "贝叶斯方法": [r"Bayesian", r"贝叶斯"],
    "马尔可夫链": [r"Markov chain", r"马尔可夫"],
    "博弈论": [r"game theory"],
    "比例风险Cox": [r"Cox proportional", r"Cox regression"],
    "模糊综合评价": [r"fuzzy (comprehensive|synthetic) evaluation", r"模糊综合"],
}

SECTIONS_RE = re.compile(
    r"^(?:(\d{1,2}(?:\.\d+)?)|[IVX]+\.|[A-Z]\.)\s+([A-Z][A-Za-z \-&]{4,60})$", re.M)

# 无编号英文标题（MCM Summary Sheet / References / Memorandum 等，v0.3 升级）
UNNUMBERED_HEADINGS = [
    "summary sheet", "summary", "references", "bibliography", "memorandum", "memo",
    "appendix", "appendices", "introduction", "background", "conclusion", "conclusions",
    "strengths and weaknesses", "strengths", "weaknesses", "model evaluation",
    "sensitivity analysis", "assumptions", "notation", "notations",
]

# 规范章节名 -> 匹配关键词（section_map 标准化字段, v0.3）
CANONICAL_SECTIONS = {
    "summary_sheet": ["summary sheet", "summary"],
    "introduction": ["introduction", "background", "问题重述"],
    "assumptions": ["assumption", "假设"],
    "notation": ["notation", "符号"],
    "model": ["model", "模型", "methodology", "求解"],
    "sensitivity": ["sensitivity", "灵敏度", "稳健性"],
    "strengths_weaknesses": ["strength", "weakness", "优缺点", "评价"],
    "conclusion": ["conclusion", "结论"],
    "memorandum": ["memorandum", "memo"],
    "references": ["reference", "参考文献", "bibliography"],
    "appendix": ["appendix", "附录"],
}


def build_section_map(sections) -> dict:
    """规范化章节映射: canonical 名 -> 原始章节文本（大小写不敏感子串匹配）"""
    smap = {}
    for canon, keys in CANONICAL_SECTIONS.items():
        for s in sections:
            low = s.lower()
            if any(k in low for k in keys):
                smap[canon] = s
                break
    return smap


def parse_id(pid: str):
    m = re.match(r"pp-(\d{4})([a-f])-(\d+)", pid)
    return m.groups() if m else (None, None, None)


def extract_abstract(text: str) -> str:
    """行级解析: Summary/Abstract 行起, 到 Keywords/首个编号章节行止"""
    NL = chr(10)
    lines = text.split(NL)
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(Abstract|ABSTRACT|摘要|Summary)\s*$", ln.strip()) and "Sheet" not in ln:
            start = i + 1
            break
        if re.match(r"^\s*(Abstract|摘要)[:：]", ln.strip(), re.I):
            return ln.split(":", 1)[-1].strip()[:3000]
    if start is None:
        return ""
    buf = []
    for ln in lines[start:]:
        s2 = ln.strip()
        if re.match(r"^(Keywords?|Key words|关键词)", s2, re.I):
            buf.append(s2)
            break
        if re.match(r"^(1[\.\s]|I\.|Introduction|2[\.\s])", s2) and len(buf) > 3:
            break
        if s2:
            buf.append(s2)
        if sum(len(x) for x in buf) > 3000:
            break
    return " ".join(buf).strip()[:3000]


def extract_sections(text: str) -> list:
    out = []
    for num, name in SECTIONS_RE.findall(text):
        n = name.strip()
        if n.lower() in {"contents", "table of contents", "abstract"}:
            continue
        out.append(f"{num} {n}".strip())
    # 无编号英文标题（v0.3: MCM Summary Sheet / References / Memorandum 等）
    for ln in text.split("\n"):
        s = ln.strip().rstrip(".:")
        low = s.lower()
        if low in UNNUMBERED_HEADINGS and len(s) <= 30 and s not in out:
            out.append(s)
    dedup = list(dict.fromkeys(out))
    return dedup[:30]


def extract_references(text: str) -> dict:
    m = re.search(r"\n\s*(?:References|REFERENCES|参考文献)\b(.{0,4000})", text, re.S)
    if not m:
        return {"count": 0, "style": "unknown", "sample": []}
    seg = m.group(1)
    entries = re.split(r"\n(?=\[\d+\]|\(\d+\)|\d{1,2}\.\s)", seg)
    entries = [e.strip() for e in entries if len(e.strip()) > 30]
    style = "numbered-brackets" if re.match(r"^\[\d+\]", entries[0]) else ("numbered" if re.match(r"^\d", entries[0]) else "other")
    return {"count": len(entries), "style": style, "sample": [e[:120] for e in entries[:3]]}


def dict_hits(text: str, table: dict) -> list:
    hits = []
    for name, pats in table.items():
        ev = []
        for pat in pats:
            for m in re.finditer(pat, text, re.I):
                line = text[max(0, m.start() - 60): m.end() + 60].replace("\n", " ").strip()
                ev.append(line)
                break  # 每模式一条证据
        if ev:
            hits.append({"name": name, "evidence": ev[0][:150]})
    return hits


def mine(pid: str, text: str) -> dict:
    year, letter, control = parse_id(pid)
    rec = {
        "id": pid, "year": int(year), "problem": letter.upper(),
        "problem_type": {"official": OFFICIAL_TYPE[letter.upper()],
                          "kb_categories": KB_CATEGORY[letter.upper()]},
        "source_path": None, "pages_scanned": None, "chars": len(text),
        "title": "", "raw_abstract": extract_abstract(text),
        "sections": extract_sections(text),
        "section_map": build_section_map(extract_sections(text)),
        "models_used": dict_hits(text, MODELS),
        "algorithms": sorted({h["name"] for h in dict_hits(text, MODELS)
                              if h["name"] in {"遗传算法", "模拟退火", "粒子群优化", "蒙特卡洛模拟",
                                                "K-means聚类", "层次聚类", "主成分分析PCA", "RK4", "二分法"}}),
        "references": extract_references(text),
        "innovation": None, "strengths": None, "weaknesses": None, "review_hooks": None,
        "authored_by": {"objective": "dictionary-miner-v0.1", "judgment": None},
        "mined_at": datetime.now().strftime("%F %T"),
    }
    # 标题: Title: 行 或 MCM Summary Sheet 格式(Control Number 后一行)
    m = re.search(r"(?:^|\n)\s*Title:?\s*(.{5,120})", text, re.I)
    if not m:
        m = re.search(r"Team Control Number[ \t]*\n[ \t]*\d+[ \t]*\n[ \t]*(\S.{5,150})", text)
    if not m:
        m = re.search(r"Summary Sheet\s*\n(\S.{5,150})\n", text)
    if m:
        rec["title"] = m.group(1).strip()
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--out-dir", default=None, help="默认 knowledge_base/paper_dataset/records")
    a = ap.parse_args()
    text = Path(a.text).read_text(encoding="utf-8")
    inv = json.loads(Path(a.inventory).read_text(encoding="utf-8"))
    src = next((p["file"] for p in inv["papers"] if p["id"] == a.id), None)
    rec = mine(a.id, text)
    rec["source_path"] = src
    out_dir = Path(a.out_dir) if a.out_dir else \
        Path(__file__).parent.parent.parent.parent / "matical model" / "knowledge_base" / "paper_dataset" / "records"
    out_dir = Path(r"E:/matical model/knowledge_base/paper_dataset/records")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{a.id}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[mine] {a.id}: models={len(rec['models_used'])} sections={len(rec['sections'])} "
          f"refs={rec['references']['count']} -> {out_dir / (a.id + '.json')}")


if __name__ == "__main__":
    main()
