---
name: night-fiction-factory
description: >
  Orchestrate multi-line overnight fiction production on the existing
  LiteraryLab Production Node: turn a natural-language night request into a
  NightPlan, allocate a global worker budget, launch staggered production
  lines, watch for upstream outages (circuit breaker) and memory pressure
  (commit gate), resume crashed lines without rewriting successful works, and
  produce a morning report. Use when the user asks things like 今晚开 N 条小说
  生产线 / 帮我写 500 篇小说跑到早上 / 继续昨晚没跑完的生产线 / 看看昨晚生产了
  多少篇 / 有失败的就恢复不要重写 / 停止某条生产线.
metadata:
  author: night-fiction-factory v1.0
  version: "1.0"
---

# Night Fiction Factory

**Skill = 编排知识；Production Node = 执行引擎。** 本 Skill 绝不重新实现
Writer / Critic / LLM Client / Scheduler / Storage——生成一律调用现有
`experiments/multi_worker_generation`。你不发明小说提示词，不改生产核心。

按顺序读：

1. [references/production_playbook.md](references/production_playbook.md) — 夜间生产全流程 runbook
2. [references/reliability_rules.md](references/reliability_rules.md) — resume/完成判定/停止的硬规则
3. [references/failure_modes.md](references/failure_modes.md) — 已发生过的 10 类事故：症状/判断/动作
4. [references/multi_line_strategy.md](references/multi_line_strategy.md) — 多线隔离、worker 预算、熔断

## 0. 前置：找到 Production Node

Skill 禁止硬编码工程路径。读取环境变量 `LITERARYLAB_NODE_ROOT`（指向工程根，
其下应有 `experiments/multi_worker_generation/run.py` 与 `ops/lab_control.py`）。
未设置时先问用户要路径，让它 setx 后继续；Skill 状态目录默认
`~/.night-fiction-factory/`（可用 `NFF_STATE_DIR` 覆盖）。

## 1. 把用户的话翻译成 NightPlan

先从用户话里抽取：总篇数、线数、题材标签、截止时间、provider。歧义（比如
"多开一些"）按保守默认处理并复述你的选择。然后跑：

```bash
python <skill>/scripts/plan_night.py build --lines 6 \
  --genres "科幻,悬疑,都市,奇幻,乡土,童话" --total 1200 \
  --stop-at 08:00 --provider glm --max-total-workers 12
```

| 用户说法 | 落成参数 |
|---|---|
| "今晚写 500 篇" | `--total 500`，线数默认 `min(4, ceil(total/150))` |
| "开 4 条线，每条不同题材" | `--lines 4 --genres ...`（题材只作标签，见 §6） |
| "科幻 200 悬疑 200 都市 100" | `--lines 3 --genres "科幻,悬疑,都市" --targets "200,200,100"` |
| "早上八点前结束" | `--stop-at 08:00` |
| "GLM 生成" | `--provider glm`；"继续昨天的线" → 走 §3 resume |

计划写入 `~/.night-fiction-factory/plans/<plan_id>.json` 与 night_registry.json。
模板见 [templates/night_plan.example.json](templates/night_plan.example.json) 与
[templates/line_config.example.json](templates/line_config.example.json)。

## 2. 标准夜间流程（一次会话做完，无人值守）

```bash
# 1) 资源门禁：commit headroom < 6GB 时禁止启动（exit 1）
python <skill>/scripts/resource_gate.py

# 2) 启动（自动：网络探测 → 逐线过门禁 → 错峰 45s → 记录 PID）
python <skill>/scripts/launch_lines.py --plan night_YYYYMMDD --probe-real

# 3) 挂上夜间守护（熔断 + 资源守卫 + 断线自动续跑 + stop_at 收尾 + 晨报）
python <skill>/scripts/night_watch.py --plan night_YYYYMMDD \
  --interval 240 --auto-resume-upstream
```

`--probe-real` 会做一次真实最小 LLM 调用（node_check probe）破网关 /health
假绿；若调用会产生费用而用户未确认，去掉它，只用默认 TCP 探测。
night_watch 前台运行即可；会话结束时告知用户进程 PID 与日志位置
（`~/.night-fiction-factory/logs/<tag>.launch.log`）。

## 3. 恢复（"继续没跑完的，别重写成功的"）

```bash
python <skill>/scripts/resume_lines.py --plan night_YYYYMMDD
```

固定语义：done / recovered_success 永远跳过；stale claimed 由引擎回收（先查
产物，完整→恢复成功，缺→回 pending）；**failed 永不静默重试**——脚本会报告
`FAILED_UNITS_REQUIRE_EXPLICIT_RETRY`。用户明确要求重试失败单元时才加
`--retry-failed --yes-rewrite-state`（先备份 state.json 再改写，写审计日志）。
把这条代价讲给用户听，拿到确认再执行。

## 4. 查看与验收

```bash
python <skill>/scripts/status_lines.py --plan night_YYYYMMDD --with-breaker
python <skill>/scripts/validate_outputs.py --plan night_YYYYMMDD --report
```

status 输出各线 DONE/TOTAL/WORKERS/STATUS、总进度、存活 worker、commit、
网络。validate 做完成判定 + 逐单元产物核对（metadata 自洽 + content.md 非空 +
work_id 唯一）。**严禁把 pending==0 当 completed**：只有 done+recovered==target
且 failed==0 且 claimed==0 且 pending==0 才是 COMPLETED；有成功有失败必须报
COMPLETED_WITH_FAILURES / FAILED_WITH_RESULTS，不冒充成功。

## 5. 停止（"今晚先停" / "停都市线，其他继续"）

```bash
python <skill>/scripts/stop_lines.py --plan night_YYYYMMDD                 # 整个计划
python <skill>/scripts/stop_lines.py --plan night_YYYYMMDD --line urban_01 # 单线
```

只杀注册簿里登记、且进程表能对上 tag/run_dir 的进程树（PID 隔离 + PID 复用
防护 + 孤儿 worker 按 run_dir 圈定收割）。**绝对禁止** `taskkill /IM python.exe`
或杀任何不属于本 NightPlan 的进程（ZCode / Dashboard / Gateway / Firefly）。
停止后 state/works 原样保留，之后用 §3 续跑。

## 6. 硬边界（如实告知用户，不得伪造能力）

- **题材是标签不是注入**：引擎按内建比例混合题材/主题池，当前没有
  line-specific 创作指令通道。line.genre 用于 tag 命名、组织与报告；
  `genre_mode` 固定 `label_only`。不要宣称"科幻线只出科幻"。
- **worker 上限 9/线、三把 Key 共享**：总 worker 由全局预算决定
  （默认 12，按 commit 余量收缩），绝不 6 线 × 9。
- **provider 只存环境变量名**：glm / tju / custom_openai_compatible 三档
  profile（base/model/key 环境变量名/timeout/并发），Skill 与产物中不得出现
  任何真实 Key。
- **不修改生产核心**：熔断/门禁/重试都在 Skill 编排层实现（停进程树 + 同 tag
  resume）；需要动引擎的需求先单独说明并征得同意。

## 7. 会话示例（照这个粒度向用户汇报）

> **用户**：今晚开 4 条小说生产线，每条 250 篇，GLM 生成，早上 8 点前尽量完成。
> **你**：plan build（4 线 × 250，glm，stop_at 08:00）→ resource_gate 通过 →
> launch（错峰启动，报告每线 PID/tag/日志路径）→ night_watch
> --auto-resume-upstream。收尾汇报：目标 1000，已启动 4 线，晨报路径。

> **用户**：昨晚有两条线挂了，继续没完成的，不要重写已经成功的。
> **你**：load_registry 找到昨晚 plan_id（status_lines 确认哪两条
> FAILED_RESUMABLE/STOPPED）→ resume_lines（说明 done/recovered 跳过、failed
> 需显式重试）→ 汇报续跑 pid。

> **用户**：现在机器内存够吗？够的话再加两条线。
> **你**：resource_gate --json 看 level 与 headroom；OK 才
> plan_night build 追加线（tag 自动避让）+ launch --only 新线；
> CAUTION/BLOCK 则如实告知并给扩容所需余量。

> **用户**：停止都市线，其他继续。
> **你**：stop_lines --plan <id> --line urban_<NN>，汇报杀了哪些 PID、
> 哪些线未受影响。

## 8. Smoke test（首次接入新机器时）

先跑 mock 测试（零成本）：

```bash
cd <skill> && python -m unittest discover -s tests -v
```

再真实 2 线 × 2 篇（约 8 次单元生成）：

```bash
python <skill>/scripts/plan_night.py build --lines 2 --genres "科幻,悬疑" \
  --targets "2,2" --stop-at 23:59 --provider glm
python <skill>/scripts/launch_lines.py --plan night_YYYYMMDD --probe-real
python <skill>/scripts/status_lines.py --plan night_YYYYMMDD --with-breaker
python <skill>/scripts/validate_outputs.py --plan night_YYYYMMDD
python <skill>/scripts/stop_lines.py --plan night_YYYYMMDD   # 需要提前收工时
```

真实 API 调用可能产生费用：用户未点头前只跑 mock 测试并把上述命令给用户。
