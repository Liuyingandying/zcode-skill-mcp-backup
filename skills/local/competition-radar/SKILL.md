---
name: competition-radar
description: Firefly Personal Opportunity Radar——面向天津大学大三本科生的全球公开机会雷达（技术+非技术全类别）。当用户提到"机会雷达、比赛、竞赛、hackathon、摄影大赛、视频大赛、作文比赛、科普、创新创业、找机会、Opportunity Radar"，或每日定时简报触发时使用。复用 research-knowledge MCP 检索；绝不凭空编造机会，截止时间未经核实一律标记"未知"。
---

# Firefly Personal Opportunity Radar（v2，原 Global Competition Radar）

为天津大学**大三**本科生收集全球范围内**仍可参加**的公开机会：比赛、竞赛、Hackathon、
创新挑战、科研展示、创作与传播类活动。v2 起不再限于技术方向——目标是"个人机会池"。

## 资格与时效三条件（硬性门槛）

1. **当前日期之后仍可报名或提交**（已截止即丢弃，哪怕作品再好）；
2. **本科生有资格参加**（面向研究生/职业选手的丢弃）；
3. **国际公开，或中国高校学生可参加**（限本国人/限特定学校的丢弃，中国区选拔除外）。

## 覆盖类别（competition_type，18 类，不设方向限制）

技术：AI Agent｜AIGC｜人工智能应用｜编程/Hackathon｜FPGA｜嵌入式｜硬件创新｜机器人｜通信｜THz/6G｜光电
非技术：视频创作｜AI 视频｜公益影像｜摄影｜作文/写作｜科普传播｜创新创业

## 数据库字段（每条机会必填，未知写"未知（原因）"）

| 字段 | 说明 |
|---|---|
| `competition_type` | 上述 18 类之一 |
| `registration_required` | **是否需要提前报名**（特别标注！报名制 vs 直接提交制） |
| `registration_deadline` | 报名截止（无报名制写"无（直接提交）"） |
| `submission_deadline` | 提交截止 |
| `eligibility` | 参赛对象（含中国本科生是否可参加） |
| `official_source` | 官网/官方规则 URL |
| `verification_level` | `官方规则核实` > `官网页核实` > `交叉来源` > `聚合站待复核` |

## 输出优先级（简报与机会池的排序规则）

1. **可立即报名**（报名通道开放、时间充裕）；
2. **即将截止报名**（≤14 天，置顶并红色标注）；
3. **截止较远但价值高**（远期星标，提前规划）。
同优先级内按星级降序。

## 工作流（每日执行或按需触发）

1. **读画像**：`competition_profile.yaml`（背景、项目资产、兴趣类别、排除项）。
2. **检索**：按下方关键词矩阵调 web_search（每类别 1~3 组）+ news_search 1~2 次；
   每日轮换侧重类别，确保非技术类别每周至少覆盖一轮。年份按当前日期滚动。
3. **核实**：fetch_page 打开官方页确认：报名要求与截止、提交截止、参赛对象、费用。
   证据分级：官方规则/官网页 > 交叉来源 > 聚合站快照（必须标"待复核"）。
4. **过滤**：不满足三条件之一即丢弃；另丢弃纯数学、纯算法刷题、高费用（报名费或强制自费差旅）、
   与画像完全无交集项。
5. **评分**：★★★★★ 项目直接可战｜★★★★ 少量改造｜★★★ 值得准备（非技术类按
   "兴趣×成本×履历价值"评分，允许与项目无关但须 ★★★ 以上）。
6. **产出**：《Firefly Personal Opportunity Radar》简报（格式见下）→ 存档
   `Competition_Radar\YYYY-MM-DD.md` → **更新全球机会池 `OPPORTUNITY_POOL.md`**（去重合并）→
   ★★★★★ 或用户点名项写入 `TRACKING.yaml`（status=tracking）。

## 检索关键词矩阵 v2（可增量维护）

**技术类**（继承 v1）：AI Agent competition / LLM hackathon / MCP hackathon / AIGC 大赛 /
FPGA competition / embedded challenge / electronics design / robotics competition 2026 /
6G challenge / THz communication / 光电设计竞赛 / 集成电路创新创业
**非技术类**（v2 新增）：
- 视频创作/AI 视频：`AI video competition 2026 deadline`｜`AI film festival student`｜
  `AI视频大赛 2026 报名`｜`微电影 大学生 2026 截止`｜`公益影像 大赛 报名`
- 摄影：`student photography contest 2026 free`｜`国际摄影大赛 2026 学生`｜`手机摄影 大赛`
- 作文/写作：`大学生作文大赛 2026 报名`｜`写作比赛 截止 2026`｜`essay competition 2026 students international`
- 科普传播：`科普大赛 2026 大学生`｜`science communication competition 2026`｜`科普视频 大赛`
- 创新创业：`创新创业大赛 2026 报名 截止`｜`student startup competition 2026`｜`挑战杯 大广赛 2026`
**国际综合**：`international student competition 2026`｜`global youth challenge free online`

## 简报格式

```
# Firefly Personal Opportunity Radar
日期：YYYY-MM-DD　检索：research-knowledge MCP（N 组关键词，M 次官网核实）

## ① 可立即报名
### <名称>　<类别>　<星级>
- registration_required：<是（截止 …）/ 否（直接提交）>
- submission_deadline：…　eligibility：…　是否免费：…
- 匹配/价值：…　准备建议：…
（……）

## ② 即将截止报名（≤14 天，红色）
## ③ 截止较远但价值高
## 被过滤项简列（≤5 条 + 一句话原因）
## 检索来源（完整 URL 列表）
```

## 全球机会池（OPPORTUNITY_POOL.md）

- 位置：`D:\glm生成计划\Firefly_Workflow\Competition_Radar\OPPORTUNITY_POOL.md`；
- 每日去重合并（按名称+官方 URL 判重），保留字段即数据库七字段+星级+类别+备注；
- 已截止项**不删除**，移入"历史/已截止"节供下届参考（赛季性机会标注年度周期）；
- 池子是长期资产：类别覆盖比单日数量重要。

## 诚实条款（最高优先级）

1. 绝不凭空生成机会——每条必须附 official_source；
2. 截止时间以官网为准，二手信息标"未知"或"待复核"；
3. 检索不到就写"今日无新增"，不硬凑；
4. 非技术类机会同样核实资格与费用，警惕收费陷阱（投稿费/评审费高的标注"高费用"过滤）；
5. 输出末尾附完整"检索来源"列表。

## 与现有系统的关系

- `competition-execution` skill + 三命令：执行端；TRACKING.yaml 是交接文件；
- `OPPORTUNITY_POOL.md`：长期机会池（本雷达维护），/competition-status 可引用；
- `/competition` 命令：按需深挖，共用画像；
- 每日 9:00 自动化：加载本 skill；与每日项目简报互斥。
