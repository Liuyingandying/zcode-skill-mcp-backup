# Multi-Line Strategy — 多生产线隔离与调度

## 隔离模型（Skill 的核心价值）

每条生产线 = 一个独立引擎 run，天然隔离：

```
night_registry.json（编排层，Skill 独有）
└── plan night_20260927
    ├── line scifi_01   tag=night_20260927_scifi_01
    ├── line mystery_01 tag=night_20260927_mystery_01
    └── ...

Production Node（引擎层，每 tag 一棵完整目录树）
data/multi_worker_generation/runs/multi_worker_<tag>/
├── mw_pilot/state.json          ← 本线独有的五态断点
├── mw_pilot/works/<unit_id>/    ← 本线独有的作品
├── logs/                        ← 本线独有的 worker 日志/异常/退出记录
├── llm_calls.jsonl              ← 本线独有的计量（熔断输入）
└── storage/                     ← 本线作品库
```

隔离保证：**tag 唯一 ⇒ state/works/logs/PID/统计全唯一**。两条线共享 tag 是
唯一被明令禁止的构图（FM-9）。line_id 只是注册簿里的别名，引擎只认 tag。

## Worker 全局预算

错的分配：`6 线 × 9 workers = 54`（FM-1 的直接放大器）。

对的分配（`allocate_workers`）：

1. 预算上限 `max_total_workers`（默认 12；经验来自 FM-12：三把 Key、单元级
   3 次串行 LLM 调用，12 个 worker 后吞吐边际趋零）。
2. 内存收缩：`mem_cap = (commit_avail_gb − 2) × 8`（实测 9 worker 整树
   ~0.5GB，此公式留 2 倍余量），预算取两者较小。
3. round-robin 摊分：6 线预算 12 → 每线 2；预算 < 线数时，多余线保持
   PLANNED（资源释放后 `resume_lines.py` 会补启动）。
4. 单线 ≤9（引擎 config worker 列表上限，超出即 argparse 侧报错）。

## 错峰启动（stagger）

launch 逐线串行：启动一线 → 记录 PID → 睡 45s（可调 5~120s）→ 下一线前
**重跑资源门禁** → 不放行则余下线保持 PLANNED。目的：避免 N 线同时冷启动
造成 commit 瞬时峰值（Python 解释器 import 阶段的峰值远高于稳态）。

## 熔断与线状态机

```
PLANNED ──launch──▶ RUNNING ──完成判定──▶ COMPLETED
                       │  ▲                 COMPLETED_WITH_FAILURES
      熔断/资源守卫/手动 │  │ 上游恢复(2次探测通过)   FAILED_WITH_RESULTS
                       ▼  │
                 PAUSED_UPSTREAM / PAUSED_RESOURCE
                       │
      stop_at/手动 ──▶ STOPPED      进程全灭 ──▶ FAILED_RESUMABLE
```

- 每线熔断窗口独立（读各自 run_dir 的 llm_calls.jsonl）——科幻线的网络抖动
  不会连坐悬疑线。
- PAUSED_* 只停进程，state 不动；恢复一律同 tag resume。
- STOPPED / FAILED_RESUMABLE 的线在晨报里如实列出，与 COMPLETED 严格区分。

## 多题材的真相与 adapter 预留

当前引擎：genre 按固定比例配额、theme 从硬编码池取最低频组合，assignment 在
批次创建时固化进 state.json——**没有任何启动时注入 line-specific 创作指令的
正式通道**（无 CLI 参数、无环境变量、无 config 字段）。

因此本 Skill：

- `line.genre` 定位为**组织标签**（tag 命名、报告、验收分组），`genre_mode`
  恒为 `label_only`，绝不对外宣称"该线只出某题材"。
- 未来若引擎开放注入通道（例如 config 支持 per-run genre/profile），适配点
  已预留：launch 的 spawn 命令构造处（`launch_lines.py` 的 `cmd` 组装）与
  line_config 模板的 `engine.args`——到时只需在 NightPlan 增加
  `creative_brief` 字段并透传，不改状态机、不改注册簿。
- 严禁为绕过限制直接改 `mass_generation_v2/config.py` 的池或手工预写
  `diversity_state.json`——那是生产核心与非官方接口。
