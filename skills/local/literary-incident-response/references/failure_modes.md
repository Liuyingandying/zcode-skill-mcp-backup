# Failure Modes — 12 条故障模式完整目录

每条含：**症状 / 判断 / 动作 / 证据来源**。编号永久保留，与
`scripts/diagnose.py` 的 `FAILURE_MODES` 一一对应。

---

## FM-01 commit 耗尽 / MemoryError

- **症状**：`MemoryError`；`WinError 1455`（页面文件不足）；worker 异常退出；
  commit ≥ 92%；机器整体卡顿。
- **判断**：宿主 commit 耗尽。**关键事实：生产整树（1 调度器 + 9 worker）
  实测 commit 仅 ~0.4-0.5GB**——元凶几乎总是宿主其他进程（浏览器、桌面端、
  重复服务实例），不是生产线本身。误判成"生产太重"会导致错误地削减 worker，
  而真凶继续吃内存。
- **动作**：立即停止扩张（不新增线/worker）；已运行线按资源守卫只停不启；
  清理宿主进程或重启机器释放 commit；确认 state.json 完好后再 resume。
- **证据**：`logs/<worker>.exception.json`、GlobalMemoryStatusEx 读数。

## FM-02 辅助进程重复实例占资源

- **症状**：生产还没开始，commit 已经很高；进程表里有多个同名服务实例。
- **判断**：机器上已有重复实例在吃 commit，此时启动生产等于把 FM-01 提前引爆。
- **动作**：先清场再生产。门禁不放行就不启动——"先跑起来再说"是 FM-01 的
  直接成因。
- **证据**：PowerShell CIM 进程表 + commit 读数。

## FM-03 worker crash（done 不能丢）

- **症状**：worker 进程消失；`worker_exits.jsonl` 有记录；部分单元停在 claimed。
- **判断**：worker 异常退出，在制单元停在 claimed。**done 是终态，state 是
  tmp+os.replace 原子写的，已完成篇目不会丢。**
- **动作**：同 tag resume。stale claimed 由引擎回收（产物完整→
  `recovered_success`，缺失→`pending`）。**不要手工改 done。**
- **证据**：state.json 五态 + `logs/worker_exits.jsonl`。

## FM-04 stale claimed 滞留

- **症状**：`claimed > 0` 但没有存活 worker；heartbeat 很旧。
- **判断**：claimed 单元心跳停滞超过 `worker_stale_seconds`（默认 120s）
  且无 worker 存活。注意 heartbeat 是 **float epoch 秒**，缺失也算 stale。
- **动作**：resume（引擎启动时批量回收）。**验收时 claimed ≠ 0 一律不得判
  COMPLETED。**
- **证据**：`unit.heartbeat` 与当前时间差。

## FM-05 上游中断烧任务（拒连风暴）

- **症状**：几分钟内几十上百个单元 failed；`llm_calls.jsonl` 尾部连续
  `connection refused` / `502` / `503` / `timeout`。
- **判断**：上游不可达，每个单元各自重试 3 次（15/30s 退避）后 failed。
  **客户端无熔断、无健康检查**——引擎层面挡不住这种模式，必须在编排层拦。
- **动作**：熔断：停该线进程树 → `PAUSED_UPSTREAM`，pending 原样保留；
  网关**真实探测**恢复后同 tag resume。failed 只能显式重试。
- **证据**：`llm_calls.jsonl` 尾部连续连接类失败计数（阈值 6）。

## FM-06 Dashboard 状态漂移

- **症状**：面板数字与磁盘对不上。
- **判断**：面板有三个**不同口径**——completed=当前批次、活跃=300s 窗口、
  待办=全库累计。三个数字极易混读，历史上已造成误判。
- **动作**：一切以 `state.json` 五态 + 进程表双证据为准；汇报统一用
  `status_lines.py` 口径；**不引用面板截图当验收**。
- **证据**：state.json 与 `/api/status` 对比。

## FM-07 completed-with-failures 误判

- **症状**：`pending == 0` 被当成"全部完成"，实际有几十个 failed。
- **判断**：完成判定必须五数齐全：
  `done + recovered_success == target` **且** `failed == 0`
  **且** `claimed == 0` **且** `pending == 0`。
- **动作**：判 `COMPLETED_WITH_FAILURES` / `FAILED_WITH_RESULTS`；
  报告里失败数必须可见，**不许含在成功里**。
- **证据**：state.json 五态计数 + 逐单元产物核对。

## FM-08 start API 假失败

- **症状**：启动接口返回 500，但生产线其实已经起来了。
- **判断**：spawn 先完成，之后的留痕步骤因 D 盘 OSError 失败，异常处理
  二次崩溃（`*解包` TypeError）。
- **动作**：先查进程表有没有该 tag 的进程、再查 state 是否推进；有则忽略 500。
  **不要因为 500 再启动一遍**（会撞 FM-09）。
- **证据**：进程表 + state.json mtime。

## FM-09 同 tag 双启动

- **症状**：两个调度器跑一个 state；文件锁疯狂争抢；计数错乱。
- **判断**：同 tag 已有存活进程时又启动了一次。
- **动作**：拒绝启动，走 resume。**state 的 O_EXCL 锁是防损坏的最后一道墙，
  不是并发调度器的设计载荷。**
- **证据**：进程表按 tag 匹配（主进程 `--tag`，worker 按 run_dir 路径）。

## FM-10 断电 / D 盘闪断后 state 恢复

- **症状**：宿主机断电或虚拟内存耗尽后全树消失；读写 state 时 OSError。
- **判断**：state.json 是原子写的，**断电通常无损**（key_2001 实测：断电后
  886 篇 done 完好）。**读失败 ≠ 数据坏**——可能是 replace 瞬间或目录闪断。
- **动作**：读按指数退避重试 ≥4 次再判死；判死后**停止扩张**（不盲目重启
  全部），只 resume。
- **证据**：state.json 可解析性 + 单元计数完整性。

## FM-11 网关 /health 假绿

- **症状**：`/health` 返回正常，实际请求 502。
- **判断**：**/health 不发网络调用**，只证网关进程就绪（9-21 实证 502 时
  仍绿）。
- **动作**：用真实最小调用探测（`node_check.py probe`）；熔断恢复判定也用
  真实探测。
- **证据**：probe 结果（HTTP 状态 + 响应体）。

## FM-12 Key 与吞吐真相

- **症状**：加大 worker 数但吞吐不成比例。
- **判断**：**每单元 3 次串行 LLM 调用**（creative_plan / draft / title）才是
  吞吐瓶颈；实测 9 worker ≈ 1.5 篇/分，总 worker > 12 后收益边际极小。
  另注意：网关不转发客户端 key，config 注明的三把 Key 实际可能只有 2 个
  独立凭证（KEY_1 = KEY_2）。
- **动作**：想要更多产出时**先加线**（隔离/题材多样性），不是无脑加 worker。
- **证据**：`llm_calls.jsonl` 的 stage 分布与耗时。

---

## 新增故障模式的方法

1. 在 `scripts/diagnose.py` 的 `FAILURE_MODES` 加条目（症状/判断/动作/证据）。
2. 若可自动检测，加一个 `check_xxx()` 函数并在 `diagnose()` 里挂上。
3. 在 `tests/test_diagnose.py` 加合成场景测试，断言能识别。
4. 回到本文件补一节。

这样下次它是"被自动发现"，而不是"被人想起来"。
