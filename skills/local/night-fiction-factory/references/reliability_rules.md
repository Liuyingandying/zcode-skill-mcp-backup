# Reliability Rules — 不可违反的规则

每条规则后面都有真实事故背书（见 failure_modes.md）。冲突时以本文件为准。

## R1 Resume 语义（固化自 key_2001 实测恢复）

| 单元状态 | 处置 |
|---|---|
| `done` | 永远跳过，永不重写 |
| `recovered_success` | 永远跳过（它本来就是从磁盘产物恢复出来的成功） |
| `claimed` 且心跳停滞 >120s | 引擎 resume 时回收：先查产物（metadata 自洽 + content.md 非空 + work_id 合法），完整 → `recovered_success`；缺失 → 重置回 `pending` |
| `pending` | resume 后继续被认领 |
| `failed` | **终态，不自动重试**。无显式指令时报告 `FAILED_UNITS_REQUIRE_EXPLICIT_RETRY` |

恢复动作 = 同 tag 重发原命令（引擎 `init_batch` 幂等，绝不覆盖既有 state）。
产物级预恢复用 `run.py --recover-only --tag <tag>`（不调 LLM，先跑一遍）。

显式重试（`--retry-failed --yes-rewrite-state`）的唯一合法流程：
备份 state.json → failed→pending（attempts 归零、清 worker/claimed_at/heartbeat/
error）→ 原子写回 → 审计日志留痕。缺任何一步都不得改 state。

## R2 完成判定

```
COMPLETED := done + recovered_success == target
             AND failed == 0 AND claimed == 0 AND pending == 0
```

严禁 `pending==0 → completed`。全终态但有失败：成功率 ≥50% →
`COMPLETED_WITH_FAILURES`，否则 `FAILED_WITH_RESULTS`——不得冒充成功。
验收时逐单元核对磁盘产物 + work_id 全局唯一。

## R3 资源门禁（commit 口径，GlobalMemoryStatusEx）

| 条件 | 级别 | 动作 |
|---|---|---|
| headroom < 6GB | BLOCK | 禁止新增生产线（launch 直接拒绝） |
| commit ≥ 90% | CAUTION | 不启动新 worker（已启动的继续跑） |
| commit ≥ 92% 或可用物理 <1024MB | CRITICAL | 只停最新启动线，**绝不自动重启** |

总 worker 数由全局预算摊分（默认 12），永不允许 N 线 × 9；单线 ≤9（引擎
config worker 列表上限）。错峰启动 20~60s/线，避免瞬时 commit 峰值。

## R4 进程安全

- 只杀注册簿登记、且 `--tag <tag>`（主进程）或 run_dir 路径（worker.py）能在
  进程表对上的 PID；PID 复用（命令行不匹配）→ 拒绝杀并报告。
- 停树 = `taskkill /F /T /PID`；3 秒后按本计划各线 run_dir 收割孤儿 worker。
- 绝对禁止按映像名杀（`taskkill /IM python.exe`）；绝不碰 ZCode / Dashboard /
  Gateway / Firefly AI Pet / 其他 Python。
- 后台启动用 DETACHED（`DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`）+
  stdin=DEVNULL + 输出追加到日志 + 子进程强制 `PYTHONIOENCODING=utf-8`、
  `PYTHONUTF8=1`（否则中文标题会让 worker UnicodeEncodeError）。

## R5 熔断（Circuit Breaker）

- 触发：`llm_calls.jsonl` 尾部**连续** ≥6 条连接类失败（cannot reach /
  connection refused / HTTP 502 / 503 / timeout / getaddrinfo failed…），
  中间夹任何成功即重新计数。无计量文件时降级用 state 里 failed 单元的
  连接类错误连续计数（弱口径，需人工复核）。
- 动作：停该线进程树 → `PAUSED_UPSTREAM`，pending 单元原样保留（state 不动），
  绝不让上游中断把几百个单元烧成 failed（key_2001 的 03:30 模式）。
- 恢复：网关连续 2 次探测通过 → 同 tag resume。恢复判定用真实探测
  （node_check probe），不信 `/health`（假绿：上游 502 时仍可全绿）。

## R6 存储与读取（D 盘闪断对策）

- Skill 的所有写：tmp + flush + fsync + `os.replace`，OSError 指数退避重试。
- 读 state/registry：JSON 解析失败或 OSError 按指数退避重试（≥4 次），
  不立即判死。
- 注册簿是编排唯一事实源；引擎 state 是生产唯一事实源；两者都不在时拒绝
  操作并提示，不猜。

## R7 审计

启动、停止、续跑、改写 state、熔断、资源守卫——每个改变世界状态的动作都写
`~/.night-fiction-factory/audit.log`（时间 + plan + line + tag + 关键数字）。
事后任何"昨晚到底发生了什么"的问题，答案先从审计日志找。
