# Failure Modes — 真实发生过的事故（症状 / 判断 / 动作）

全部条目来自真实生产事故与恢复演练，不是理论风险。编号永久保留。

## FM-1 key_2001 MemoryError（03:30 全树终止）

- **症状**：worker 在 `claim_next → read_state` 抛 `MemoryError`；
  `logs/<worker>.exception.json` 留有现场；伴随 `WinError 1455`（页面文件不足）。
- **判断**：宿主 commit 耗尽。注意：生产整树（1 调度器 + 9 worker）commit 仅
  ~0.4-0.5GB——元凶几乎总是宿主上其他进程（辅助服务/浏览器/重复实例），
  不是生产线本身。
- **动作**：启动前过资源门禁（headroom ≥6GB）；运行中 commit ≥92% 只停不启；
  断电/全灭后不要急于重启——state 是原子写的，先读 state 五态再决定
  （见 FM-10）。

## FM-2 辅助进程重复实例吃资源（teach_mcp 事件）

- **症状**：启动生产前机器已有一堆同名 Python 服务实例；commit 已经很高。
- **判断**：`resource_gate.py` CRITICAL/BLOCK；用进程表（PowerShell CIM）看
  谁在吃 commit。
- **动作**：先清场再生产；门禁不放行就不启动——"先跑起来再说"是 FM-1 的
  直接成因。

## FM-3 worker crash 但 done 不能丢

- **症状**：worker 进程消失，`worker_exits.jsonl` 出现记录，部分单元停在
  `claimed`。
- **判断**：claimed + 心跳停滞 >120s = stale（heartbeat 是 float epoch 秒，
  与 config `worker_stale_seconds=120` 同源）。
- **动作**：同 tag resume。done 是终态，state 原子写保证已完成的篇目完好；
  stale claimed 由引擎回收（产物完整 → `recovered_success`，缺失 → pending）。
  不要手工改 done。

## FM-4 stale claimed 长期滞留

- **症状**：state 里 claimed 单元计数不为 0 且 heartbeat 很旧，生产却停了。
- **判断**：`stale_claimed(units, 120)` 非空且无存活 worker。
- **动作**：resume（引擎启动时 `_reclaim_stale` 批量回收）。验收时 claimed≠0
  一律不得判 COMPLETED。

## FM-5 上游中断烧任务（connection refused 风暴）

- **症状**：网关/TJU 上游不可达，每个单元各自重试 3 次（15/30s 退避）后
  failed；几分钟内几十上百个单元烧成 failed。
- **判断**：`llm_calls.jsonl` 尾部连续连接类失败（客户端无重试无熔断，重试
  只在单元级——引擎层面挡不住这种模式）。
- **动作**：Skill 层熔断：连续 ≥6 条连接类失败 → 停树 → PAUSED_UPSTREAM，
  pending 原样保留；网关恢复（真实探测，非 /health）后 resume。failed 只能
  显式重试（R1）。

## FM-6 Dashboard 状态漂移

- **症状**：面板显示的 completed/pending 与磁盘对不上（口径：completed=当前
  批次、活跃=300s 窗口、待办=全库累计，三个数字极易混读）。
- **判断**：一切以 `<run_dir>/mw_pilot/state.json` 五态 + 进程表双证据为准。
- **动作**：汇报口径统一为 status_lines.py 的输出；不引用面板截图当验收。

## FM-7 completed-with-failures 误判

- **症状**：`pending==0` 被当成"全部完成"，实际有几十个 failed。
- **判断**：完成判定必须五数齐全（R2）：done+recovered==target 且 failed==0
  且 claimed==0 且 pending==0。
- **动作**：validate_outputs.py 判 COMPLETED_WITH_FAILURES /
  FAILED_WITH_RESULTS；报告里失败数必须可见，不许"含在成功里"。

## FM-8 start API 假失败

- **症状**：启动接口返回 500，但生产线其实已经起来了（spawn 先完成，
  之后的留痕步骤因 D 盘 OSError 失败，异常处理二次崩溃）。
- **判断**：先查进程表里有没有该 tag 的进程、再查 state 是否在推进；
  有则忽略 500。
- **动作**：不要因为 500 就再启动一遍（会撞 FM-9）。Skill 的 launch 每启动
  一线立即落注册簿，就是为了把这种不一致窗口压到最小。

## FM-9 同 tag 双启动

- **症状**：两个调度器同时跑一个 state；文件锁疯狂争抢，计数错乱。
- **判断**：launch 前 `match_line_pids` 查到该 tag 已有存活进程。
- **动作**：拒绝启动并提示 resume_lines.py。state 的 O_EXCL 锁是防损坏的
  最后一道墙，不是并发调度器的设计载荷。

## FM-10 断电 / D 盘闪断后的 state 恢复

- **症状**：宿主机断电或虚拟内存耗尽后全树消失；或读写 state 时 OSError。
- **判断**：state.json 是 tmp+os.replace 原子写的，断电无损（key_2001 实测：
  断电后 886 篇 done 完好）。读失败≠数据坏，可能是 replace 瞬间或目录闪断。
- **动作**：读按指数退避重试 ≥4 次再判死；判死后停止扩张（不盲目重启全部），
  只 resume。Skill 自己的写全部走同一原子范式。

## FM-11 网关 /health 假绿

- **症状**：`/health` 返回正常（providers configured），实际请求 502。
- **判断**：/health 不发网络调用，只证网关进程就绪。
- **动作**：夜跑前 `--probe-real`（node_check probe，真实最小调用）；
  熔断恢复判定也用真实探测。

## FM-12 三把 Key 与吞吐真相

- **症状**：加大 worker 数但吞吐不成比例。
- **判断**：网关不转发客户端 key，三把 Key 互不相同且共享于全部 worker；
  每单元 3 次串行 LLM 调用（plan/draft/critic）才是吞吐瓶颈，实测 ~1.5 篇/分
  （9 worker）。总 worker >12 后收益边际极小而资源风险上升。
- **动作**：全局预算默认 12；想要更多产出时先加线（隔离/题材多样性），
  不是无脑加 worker。
