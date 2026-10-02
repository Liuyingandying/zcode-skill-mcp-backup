# `state.json` schema（权威状态）

> **定位**：不只是"流程位置"，而是**可校验的权威状态**。
> 新会话的第一件事是**用它做启动自检**（见 `protocols/startup_verify.md`）。

```jsonc
{
  // 本文件格式版本，与本 skill 的版本号无关
  "version": "2.0.0",

  // ── 流程位置 ──
  "competition_profile": "…",
  "run_mode": "full | light",
  "phase": 0,
  "current_role": "startup | modeler | auditor | coder | writer | wrapup",
  "interaction_mode": "A | B",                       // 工作模式：A 仅协助 / B 全权代理
  "collab_mode": "agent-led | user-led | mixed",     // 分工模式，默认 mixed
  "writing_pace": "…",

  // ── 产物清单（启动自检的核心）──
  "artifacts": [
    {
      "id": "q1_model_spec",
      "path": "03_建模思路/模型规格书_<子问题>.md",
      "role": "modeler",
      "question": 1,
      "status": "draft | reviewed | final",
      "mtime": "YYYY-MM-DD HH:MM",
      "summary": "一句话说明这份产物是什么"
    }
  ],

  // ── 当前生效的参数与设定（唯一来源）──
  "active_params": {
    "q2": { "alpha": 0.20, "lambda": 0.47095, "calib_window": "…", "report_window": "…" }
  },

  // ── 已作废的内容 + 替代者 ──
  "superseded": [
    { "what": "旧的参数取值", "value": "…", "replaced_by": "…", "reason": "…", "date": "…" }
  ],

  // ── 待用户拍板 ──
  "open_questions": [
    { "id": "Q1", "question": "…", "options": ["…"], "raised": "…" }
  ],

  // ── 已确认的缺陷（供审核手交叉检查）──
  "known_issues": [
    { "id": "ISSUE-1", "question": 2, "type": "信息时序", "desc": "…", "status": "fixed | open" }
  ]
}
```

---

## 使用要求

1. **每问定稿、每次关键决策后立即更新**（不要攒）；
2. `active_params` 是参数的**唯一来源**——正文与文档中的数字都必须与它一致；
3. `superseded` 是"作废隔离"的依据——据此检查正文与文档里是否还残留旧值；
4. 启动自检时逐条校验 `artifacts` 的路径与时间戳，**差异为 0 才开工**。
