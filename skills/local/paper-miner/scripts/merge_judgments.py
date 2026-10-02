# -*- coding: utf-8 -*-
"""merge_judgments.py —— 把 agent 撰写的 judgment 字段并入 records, 并生成 KB meta 条目"""
import json
from datetime import datetime
from pathlib import Path

RECORDS = Path(r"E:/matical model/knowledge_base/paper_dataset/records")
META = Path(r"E:/matical model/knowledge_base/paper_dataset/meta")

OFFICIAL = {"A": "连续(Continuous)", "B": "离散(Discrete)", "C": "数据洞察(Data Insights)",
            "E": "可持续(Sustainability)"}
PROB_THEME = {
    "pp-2023a": "2023 MCM A 植物群落抗旱演替",
    "pp-2023b": "2023 MCM B 马赛马拉河水资源重塑",
    "pp-2023c": "2023 MCM C Wordle 结果数据分析",
    "pp-2023e": "2023 MCM E 光污染测量与干预",
    "pp-2024a": "2024 MCM A 七鳃鳗适应性性别比例",
    "pp-2024b": "2024 MCM B 失联潜水器搜索",
    "pp-2024c": "2024 MCM C 网球比赛动量分析",
    "pp-2025a": "2025 MCM A 楼梯磨损与建造",
    "pp-2025b": "2025 MCM B 朱诺可持续旅游",
    "pp-2025c": "2025 MCM C 奥运奖牌预测",
}

J = {
  "pp-2023a-2300336": {
    "innovation": "基于生态位理论的植物群落演替微分方程模型，将干旱胁迫映射为物种迁移/定殖参数的动态调整，实现多物种竞争-共存的机理化仿真",
    "strengths": ["机理链条完整：生态位→演替→抗旱性", "含不可预测因素的敏感性分析专章"],
    "weaknesses": ["物种参数的生态学取值依赖假设，缺数据标定", "模型验证以定性讨论为主"],
    "review_hooks": {"assumption_traps": ["生态参数无数据标定"],
                      "sanity_checks": ["参数敏感性分析完整性", "演替稳态与生态学常识对照"]}},
  "pp-2023b-2300136": {
    "innovation": "AHP 与 Logistic 增长耦合的水资源-生态联合建模，把主观赋权与种群动力学衔接",
    "strengths": ["层次清晰（背景-文献-重述-模型设计）", "多方法组合覆盖评价与预测"],
    "weaknesses": ["摘要提取缺失（版式差异），判断基于章节与词典证据，置信度较低", "AHP 主观性未见一致性检验证据"],
    "review_hooks": {"assumption_traps": ["AHP 权重主观性", "Logistic 环境容量取值"],
                      "sanity_checks": ["AHP 一致性比率 CR<0.1", "增长率参数来源可追溯"]}},
  "pp-2023c-2300348": {
    "innovation": "GRU 时序预测与 GSRF(广义随机森林) 分类模型组合，并系统分析单词属性与报告率的关系",
    "strengths": ["预测/分类/关联三层分析结构完整", "多模型准确性对照讨论专章"],
    "weaknesses": ["深度模型在 ~500 样本量级存在过拟合风险", "特征工程依赖游戏版本假设"],
    "review_hooks": {"assumption_traps": ["小样本深度学习过拟合", "时序划分泄漏"],
                      "sanity_checks": ["训练/验证划分合理性", "基线模型对照"]}},
  "pp-2023e-2301428": {
    "innovation": "光污染构成分解 + AHP/熵权组合赋权的综合评价框架，并给出可移植的干预策略分层",
    "strengths": ["组合赋权降低单一主观性", "从测量到干预的闭环结构"],
    "weaknesses": ["评价指标的数据覆盖面有限", "干预效果未量化回评"],
    "review_hooks": {"assumption_traps": ["指标权重敏感性", "数据代表性"],
                      "sanity_checks": ["组合权重稳定性", "评价结果排序的领域合理性"]}},
  "pp-2024a-2400996": {
    "innovation": "自适应性别比例的七鳃鳗种群迭代模型，将性别比例的可塑性作为种群-生态系统反馈变量",
    "strengths": ["机理迭代模型与生态问题贴合", "Model I/II 分层组织清晰"],
    "weaknesses": ["性别决定机制简化为比例调节，缺分子生态依据", "生态系统反馈项的标定不足"],
    "review_hooks": {"assumption_traps": ["性别比例调节机制的生物学依据", "迭代格式数值稳定性"],
                      "sanity_checks": ["种群不灭绝/不发散", "参数扰动下的定性稳定性"]}},
  "pp-2024b-2407038": {
    "innovation": "洋流动力学回归与数据驱动预测混合的潜水器轨迹模型，配贝叶斯更新的动态搜索策略",
    "strengths": ["动力学先验+数据修正的混合建模范式", "搜索-定位闭环（预测→规划→更新）"],
    "weaknesses": ["对洋流数据精度/分辨率敏感", "蒙特卡洛与遗传算法组合的计算成本讨论不足"],
    "review_hooks": {"assumption_traps": ["洋流场稳态假设", "搜索模型对定位误差的敏感性"],
                      "sanity_checks": ["轨迹预测的物理一致性", "搜索收益递减检查"]}},
  "pp-2024c-2401298": {
    "innovation": "提出 Dual-Temporal Bayesian Network 双时态贝叶斯网络刻画动量的双向时间尺度，配发球/接发球重加权与滑动窗口 AUC",
    "strengths": ["概念定义可操作化（重加权策略）", "多角度验证动量存在性（窗口/AUC）"],
    "weaknesses": ["贝叶斯网络结构学习依赖先验设定", "单赛事数据的泛化性"],
    "review_hooks": {"assumption_traps": ["动量定义的循环论证风险", "网络结构先验主观性"],
                      "sanity_checks": ["特征-动量的因果vs相关辨析", "显著性检验完整性"]}},
  "pp-2025a-2500836": {
    "innovation": "以磨损微分方程刻画楼梯使用历史，反演人流量与使用模式，联立建造时长估计",
    "strengths": ["正向机理+反向反演的双向使用", "PSO 处理非凸反演问题"],
    "weaknesses": ["磨损率常数缺乏材料学标定", "多因素(维修/更换)干扰未充分讨论"],
    "review_hooks": {"assumption_traps": ["磨损率恒定假设", "反演不适定性"],
                      "sanity_checks": ["反演解的唯一性/稳定性", "蒙特卡洛不确定度量化"]}},
  "pp-2025b-2501687": {
    "innovation": "可持续旅游三层次(经济/社会/环境)指标体系 + Logistic 承载力约束下的线性规划策略优化",
    "strengths": ["指标体系完整并落到可执行策略", "模型结果直接给出政策建议与应用迁移"],
    "weaknesses": ["ARIMA 与 LP 的衔接假设较强", "PCA 降维后的解释性折损未讨论"],
    "review_hooks": {"assumption_traps": ["承载力阈值设定", "指标体系权重敏感性"],
                      "sanity_checks": ["优化解的约束完全满足", "敏感性分析覆盖关键权重"]}},
  "pp-2025c-2500759": {
    "innovation": "奖牌分布预测-突破国识别-项目表现评估-教练资源分配的动态耦合综合框架，多源数据融合",
    "strengths": ["多模型(9 类)分层组合且各司其职", "从预测延伸到资源分配的决策闭环"],
    "weaknesses": ["模型堆叠的组合误差传播未系统分析", "部分模型(博弈论)使用深度存疑"],
    "review_hooks": {"assumption_traps": ["模型组合的误差传播", "数据获取时点的窗口效应"],
                      "sanity_checks": ["各子模型独立验证", "耦合接口的一致性检查"]}},
}

for pid, jd in J.items():
    rec_file = RECORDS / f"{pid}.json"
    rec = json.loads(rec_file.read_text(encoding="utf-8"))
    rec["innovation"] = jd["innovation"]
    rec["strengths"] = jd["strengths"]
    rec["weaknesses"] = jd["weaknesses"]
    rec["review_hooks"] = jd["review_hooks"]
    rec["authored_by"]["judgment"] = "agent-llm(GLM-5.3-Flash)"
    rec["title"] = rec["title"] or f"{PROB_THEME[pid[:8]]} O奖论文"
    rec_file.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    # KB meta 条目
    year, problem = rec["year"], rec["problem"]
    meta = {
        "id": pid, "layer": "paper_dataset",
        "title": f"{PROB_THEME[pid[:8]]} O奖论文 ({pid})",
        "tags": ["竞赛论文", "美赛", "O奖", f"{year}", f"{problem}题"],
        "problem_types": rec["problem_type"]["kb_categories"],
        "keywords": [m["name"] for m in rec["models_used"]][:8] + [OFFICIAL[problem]],
        "source": {"origin": rec["source_path"], "refs": [], "verified": datetime.now().strftime("%F")},
        "confidence": "draft",
        "created": datetime.now().strftime("%F"),
        "record": f"records/{pid}.json",
        "award": "Outstanding",
    }
    META.mkdir(parents=True, exist_ok=True)
    (META / f"{pid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print("merged 10 records + 10 meta entries")
