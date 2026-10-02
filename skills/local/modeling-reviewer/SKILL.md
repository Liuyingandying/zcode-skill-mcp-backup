---
name: modeling-reviewer
description: 数学建模质量审查 skill（Reviewer 阶段）。当用户提到"审查模型、检查假设、目标函数合理性、变量关系方向、极端情况、模型风险报告、review 建模方案"，或在建模/编程阶段完成后要求质量控制时使用。以 ANALYSIS_MODELING_REPORT.md 与 RESULTS_REPORT.md 为输入，输出带严重级别的 RISK_REPORT.md。独立于生成阶段，不修改任何生成 skill 的产物，只提风险与证据。
---

# Modeling Reviewer —— 模型质量审查

定位：生成阶段（2analysis → 6verity）之后的独立质量门。源于 run_001 的核心教训——**题目没给显式目标函数时，建模者自造的目标函数可能方向性错误且不自知**（Q2 案例曾把"风险最小"实现成与临床相反的解）。

## 硬性约束

1. 只读生成产物，不修改；只产出风险报告。
2. 每条风险必须带**证据**（文件:数值 或 推理链），无证据的风险标记为"假设待验证"。
3. 严重级别：`CRITICAL`（方向性/原理性错误，结果不可用）｜`HIGH`（影响主结论，需返工）｜`MEDIUM`（影响次要结论或稳健性存疑）｜`LOW`（完善性建议）｜`FLAG`（自动探针命中，需人工判读）。

## 工作流程

### Step 1: 清单式人工审查（读 ANALYSIS_MODELING_REPORT.md）
按 `references/checklists.md` 逐项过：
- **假设清单**：把报告/代码中的显式与**隐含**假设全部列出（隐含假设是高发区，如"用首测值代表整个孕期"）。
- **目标函数来源表**：逐问标注目标函数是题目给定还是自造；**自造者必须附方向性 sanity check 记录**（极端案例/单调性/领域常识对照）——没有者直接 HIGH。
- **承诺-兑现对账**：分析报告承诺的检验（如"PH 假设粗检"）逐条到代码里找兑现。

### Step 2: 自动探针（写 review_spec.json 后运行脚本）
把可机械判定的检查写进 spec，运行：
```bash
python ~/.zcode/skills/modeling-reviewer/scripts/review.py --spec review_spec.json --out RISK_REPORT.md
```
spec 支持：方向检查（系数/HR 符号与领域预期）、单调性检查（分组结果沿物理量应单调）、边界检查（值域/网格）、小样本 FLAG（组 n 阈值）、JSON 标量检查（dot-path）。

### Step 3: 极端情况探针（人工+轻量脚本）
至少执行：留一稳定性（剔除小样本组后结论是否保持）、网格/阈值端点行为、噪声扰动的结论翻转测试。探针结果写进报告。

### Step 4: 汇总 RISK_REPORT.md
结构：`审查范围 → 自动探针结果(表) → 假设风险 → 目标函数风险 → 方向/边界/极端 → 承诺未兑现 → 结论与修复优先级`。
结论给出：可否进入下一阶段（论文/提交）或必须返工的项。

## optimization_review（优化类问题专项，run_003 起启用）

生成阶段涉及求解/优化/定位/寻优时，在 Step2 之后加跑：

```bash
python ~/.zcode/skills/modeling-reviewer/scripts/optimization_review.py \
  --spec opt_review_spec.json --results-dir <结果目录> --out opt_review_section.md
```

五个维度（前四项 spec 声明 + 人工复核，第五项自动执行）：
1. **目标函数定义**：题目给定还是自造？自造者必须有 sanity check 记录
2. **变量可观测性**：哪些量可观、哪些不可观（旋转不变/尺度不变等），不可观测性如何补偿
3. **约束完整性**：每条约束是否在代码中真实强制（要有 evidence 指向代码）
4. **边界条件**：退化情形（参数→0/∞、缺角、病态几何）的行为与处理
5. **优化结果验证**：自动阈值断言 + 可执行校验脚本（round-trip、一致性重算），exit!=0 即 FAIL

> 灵感源：run_003 的"初始模型断言三夹角唯一解，被 44.6% 未消解率证伪（等角共轭二义）"——
> 求解器跑通≠数学正确，本节专防此类错误。

## physics_review（机理类问题专项，run_004 起启用）

生成阶段涉及物理机理建模/数值求解时，在 Step2 之后加跑：

```bash
python ~/.zcode/skills/modeling-reviewer/scripts/physics_review.py \
  --spec physics_review_spec.json --results-dir <结果目录> --exp-dir <代码目录> --out physics_section.md
```

五个维度：
1. **方程量纲一致性**：每条机理方程声明 LHS/RHS 量纲并核对；单位换算（如 cm/min→cm/s）须在代码中定位
2. **初始/边界条件完整性**：IC/BC 逐条声明并核验代码落地（初值、炉口/炉尾环境温度等）
3. **参数来源可追溯**：每个参数标注 given-by-problem / identified；辨识参数必须附辨识报告与残差，合成基准下可加"已知真值容差"检查
4. **黑箱替代检查**：扫描实验代码中的 ML 库引用（sklearn/torch/lightgbm 等）——机理题出现即 FLAG；机理要素（热平衡方程、传热系数）必须在代码中落地而非只写在报告里
5. **数值求解稳定性**：步长减半的 Richardson 对比，输出相对变化量并对照阈值

> 灵感源：run_004 的动机——机理题最容易败在"看起来有机理、实际是曲线拟合"，
> 以及辨识参数无报告、求解步长不收敛检查。本节专防此类问题。
