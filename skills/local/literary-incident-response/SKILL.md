---
name: literary-incident-response
description: >
  Diagnose and respond to LiteraryLab production incidents: map a symptom
  (MemoryError, mass failures, stale claimed units, state drift, fake
  completion, double launch, dashboard mismatch) to a known failure mode with
  evidence, then give the exact recovery action. Use when the user says 生产
  出问题了 / 昨晚挂了 / 为什么这么多失败 / 状态对不上 / 是不是内存爆了 /
  任务卡住了 / 帮我看看哪里坏了 / 恢复一下 / 事故复盘, or when a production
  run ends with failures, hangs, or inconsistent counts.
metadata:
  author: literary-incident-response v1.0
  version: "1.0"
---

# Literary Incident Response

**只诊断，不擅自动手。** 本 Skill 的产出是「判断 + 证据 + 建议动作」，
修复动作由人确认后执行（或交给 `night-fiction-factory` 的 resume/stop）。

事故知识来源：本仓库 25+ 份 `*_REPORT.md` 与真实事故（key_2001 断电、
teach_mcp 资源挤占、Dashboard 状态漂移、start API 假失败等），已固化成
12 条故障模式（FM-01..FM-12）与可执行诊断器。

先读：[references/failure_modes.md](references/failure_modes.md)（12 条完整目录）、
[references/diagnosis_protocol.md](references/diagnosis_protocol.md)（诊断流程与
证据规则）。

## 1. 一键诊断

```bash
python <skill>/scripts/diagnose.py --node-root <Production Node 根>
python <skill>/scripts/diagnose.py --node-root <根> --tag key_2001
python <skill>/scripts/diagnose.py --node-root <根> --json     # 机器可读
python <skill>/scripts/diagnose.py --list                      # 列出全部故障模式
```

诊断器**只读**，检查项：

| 检查 | 覆盖故障 |
|---|---|
| `memory` | FM-01/02：commit 分级（OK/CAUTION/BLOCK/CRITICAL） |
| `worker_exceptions` | FM-01/03：扫描 `logs/*.exception.json`，识别 MemoryError/1455 |
| `unit_states` | FM-04/07：五态完整性、stale claimed、完成判定 |
| `breaker` | FM-05：`llm_calls.jsonl` 尾部连续连接类失败 |
| `artifacts` | FM-03/07：done 单元产物完整性（metadata 自洽 + content 非空） |
| `double_launch` | FM-09：同 tag 多调度进程 |

退出码：0=健康或仅证据缺口，1=发现需处置的问题，2=诊断器无法运行。

## 2. 症状 → 故障模式速查

| 用户描述 | 大概率是 | 先看 |
|---|---|---|
| "内存爆了 / MemoryError" | FM-01 | `worker_exceptions` + `memory` |
| "启动前机器就很卡" | FM-02 | `memory` + 宿主进程表 |
| "worker 挂了" | FM-03 | `unit_states` + `worker_exits.jsonl` |
| "任务卡住不动了" | FM-04 | `unit_states` 的 stale claimed |
| "一大批失败" | FM-05 | `breaker` |
| "面板数字对不上" | FM-06 | `unit_states`（以 state 为准） |
| "显示完成了但感觉不对" | FM-07 | `unit_states` 五数 + `artifacts` |
| "启动报 500" | FM-08 | `double_launch` + state mtime |
| "好像跑了两次" | FM-09 | `double_launch` |
| "断电了 / 读文件报错" | FM-10 | `unit_states` 可解析性 |
| "网关正常但请求失败" | FM-11 | 真实探测（非 /health） |
| "加 worker 没变快" | FM-12 | `breaker` 的 stage 分布 |

## 3. 处置动作（按级别）

**CRITICAL** —— 立即停手，不要扩张：
- commit 触及停止线 → 只停不启；清理宿主进程或重启释放
- 熔断（连续 ≥6 连接类失败）→ 停该线进程树 → `PAUSED_UPSTREAM`，
  pending 原样保留；网关**真实探测**恢复后同 tag resume
- 缺产物 / 双启动 → 人工介入，不得自动 resume

**BLOCK / CAUTION** —— 禁止新增，已运行的继续：
- headroom < 6GB → 不新增线
- commit ≥ 90% → 不新增 worker

**WARN** —— 记录并观察：
- stale claimed → resume 时引擎自动回收
- failed > 0 → **不静默重试**；报告 `FAILED_UNITS_REQUIRE_EXPLICIT_RETRY`，
  需用户明确同意才走显式重试（先备份 state.json）

**UNKNOWN** —— 证据不足，说明缺什么，不猜、不谎报健康。

## 4. 恢复动作（确认后执行）

诊断给出方向后，恢复本身交给 `night-fiction-factory`：

```bash
python <night-fiction-factory>/scripts/resume_lines.py --plan <plan_id>
python <night-fiction-factory>/scripts/stop_lines.py   --plan <plan_id> [--line X]
```

**永不**：手工改 done、`--fresh` 覆盖、按映像名杀进程、静默重试 failed。

## 5. 复盘（事后）

事故结束后写一份复盘，包含：时间线、首个异常信号、根因、处置、**本可提前
发现它的检查项**。若发现新的故障模式，补进
[references/failure_modes.md](references/failure_modes.md) 并给诊断器加检查项
（`scripts/diagnose.py` 的 `FAILURE_MODES` 与 `check_*` 函数）——
这样下次它是"被自动发现"而不是"被人想起来"。

## 6. 测试

```bash
cd <skill> && python tests/test_diagnose.py
```

42 项测试用合成故障场景验证识别能力（MemoryError、熔断、stale claimed、
缺产物、伪完成、双启动、内存分级、UNKNOWN 不拉低结论等）。
