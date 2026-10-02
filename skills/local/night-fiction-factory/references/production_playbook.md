# Production Playbook — 夜间生产全流程

本 runbook 面向"用户晚上下一条命令，系统自己跑几小时，早上看报告"的场景。
所有命令由 Z Code 会话执行；脚本只编排，生成全部由现有 Production Node 完成。

## T-1：前置确认（一次性）

1. **Node 发现**：`LITERARYLAB_NODE_ROOT` 指向工程根。校验标记：
   `experiments/multi_worker_generation/run.py` + `ops/lab_control.py` 存在。
2. **网关**：LLM 依赖本地网关（provider profile 的 base_url，默认
   `http://127.0.0.1:8000/v1`）。launch 默认做 TCP 探测；`/health` 存在假绿
   （不证上游可用），要放心的夜跑加 `--probe-real`（node_check probe，
   一次真实最小调用）。
3. **资源**：`resource_gate.py`。commit headroom < 6GB → 禁止启动（这是
   bootstrap.ps1 同源的 FAIL 级门禁，不是建议）。
4. **Key**：三把 TJULLM Key 存在 env / HKCU 注册表。Skill 只引用环境变量
   名，永不读值、不落盘。

## T0：计划与启动

```
plan_night.py build      # 生成唯一 tag、worker 预算、写注册簿
resource_gate.py         # 若 build 之后环境有变，再确认一次
launch_lines.py          # 逐线：fresh 校验 → 门禁 → DETACHED spawn → 记 PID
night_watch.py           # 守护循环（采样/熔断/守卫/自动续跑/stop_at/晨报）
```

launch 对每条线的分类处理（`classify_launch`）：

| 情形 | 动作 |
|---|---|
| run 目录不存在 | fresh 启动 |
| state 存在且已终态 | 跳过，注册簿记终态（**永不重跑**） |
| state 存在未完成且进程存活 | 拒绝（防同 tag 双启动） |
| state 存在未完成且进程不在 | 拒绝，提示走 resume_lines.py |
| run 目录存在但无 state.json | 拒绝（脏目录，人工处理，绝不删） |

启动命令（每线，DETACHED，stdout→`~/.night-fiction-factory/logs/<tag>.launch.log`）：

```
python experiments/multi_worker_generation/run.py --limit <target> --workers <w> --tag <tag>
# cwd = LITERARYLAB_NODE_ROOT（引擎按相对路径加载 .env）
# 退出码：0=completed，1=failed/failed_with_results，2=网关硬阻断
```

## T+：守护期（night_watch 每轮）

1. 读各线 `state.json` 五态计数（pending/claimed/done/failed/recovered_success）。
2. 熔断：该线 `llm_calls.jsonl` 尾部连续 ≥6 条连接类失败 → 停树 →
   `PAUSED_UPSTREAM`；`--auto-resume-upstream` 时网关连续 2 次探测通过后同 tag 续跑。
3. 资源守卫：commit ≥92% 或可用物理 <1024MB → 只停最新线（`PAUSED_RESOURCE`，
   pilot-100 语义：只停不自动重启）。
4. 进程全灭但 state 未完成 → `FAILED_RESUMABLE`（默认不自动续跑）。
5. 每 tick 采样落 `samples/<plan>.jsonl`（供晨报的 commit 峰值/恢复次数）。
6. `stop_at` 到点 → 全部安全停止 → 写 `NIGHT_PRODUCTION_REPORT_<plan>.md`。

## T+1：早晨验收

```
status_lines.py --plan <id> --with-breaker    # 各线状态总览
validate_outputs.py --plan <id> --report      # 完成判定 + 逐单元产物核对
```

向用户汇报：目标 vs 实际成功、失败数与 `FAILED_UNITS_REQUIRE_EXPLICIT_RETRY`
提示、熔断/守卫触发次数、commit 峰值、晨报与作品目录路径
（`<run_dir>/mw_pilot/works/<unit_id>/content.md`）。

## 数据与状态分布（谁记录什么）

| 层 | 位置 | 内容 |
|---|---|---|
| NightPlan | `~/.night-fiction-factory/plans/<plan_id>.json` | 计划本体 |
| 注册簿 | `~/.night-fiction-factory/night_registry.json` | 各线 tag/pid/status/计数（编排唯一事实源） |
| 引擎 state | `<node>/data/multi_worker_generation/runs/multi_worker_<tag>/mw_pilot/state.json` | 五态单元（引擎事实源，Skill 只读） |
| 作品 | `<run_dir>/mw_pilot/works/<unit_id>/content.md` | 每单元产物 |
| 计量 | `<run_dir>/llm_calls.jsonl` | 每次调用的 ok/error（熔断输入） |
| 审计 | `~/.night-fiction-factory/audit.log` | 启动/停止/改写 state 的一生 |

两层事实源刻意分开：Skill 永不改引擎 state（显式重试除外，见
reliability_rules.md），引擎也不知道注册簿存在。
