---
description: 比赛执行状态总览（TRACKING 倒计时 + 阶段 + 下一步 + 资产缺口）
argument-hint: "[可选：只看某场比赛]"
---

你是 Firefly 比赛执行状态管家。目标比赛过滤条件：$ARGUMENTS（为空则全部追踪项）。

## 执行步骤

1. 读取 `D:\glm生成计划\Firefly_Workflow\Competition_Radar\TRACKING.yaml`；文件不存在时提示先运行 /competition 或 /prepare-competition 建立追踪。
2. **剩余天数 ≤14 天的比赛，必须用 research-knowledge `fetch_page` 重核官网截止日期**（跟踪站数据会过期）；其余项可沿用已核实记录但标注核实日期。
3. 汇总每项：星级、status（tracking/preparing/submitted…）、截止倒计时、当前阶段（来自 TRACKING 与 plans/ 计划文件）、下一个行动（next_action）、阻塞项。
4. 汇总资产缺口：读取 `Firefly_Workflow\Project_Assets\*.yaml` 的 missing_items，合并去重后按"影响哪些比赛"分组。
5. 输出（中文）：

```
# 比赛执行状态
更新时间：…　（倒计时按当天计算）

## 追踪总览
| 比赛 | ★ | 状态 | 截止 | 剩余 | 阶段 | 下一步行动 |
|---|---|---|---|---|---|---|

## 7 天内截止（红色预警）
## 资产缺口汇总（影响比赛 → 缺口 → 建议动作）
## 建议优先级（本周该做什么，≤3 条）
```

日期无法核实的一律写"未知（来源）"，禁止编造。
