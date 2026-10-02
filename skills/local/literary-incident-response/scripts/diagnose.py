#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事故诊断器：把散落在 25+ 份 *_REPORT.md 里的判断逻辑固化成可执行代码。

设计原则：
- **只读**。诊断不修改任何生产数据；修复动作由人确认后另行执行。
- **多证据**。每个结论都列出支撑证据与反证，不靠单一信号下判断。
- **诚实降级**。证据不足时输出 UNKNOWN 并说明缺什么，不猜。

用法：
  python diagnose.py --node-root D:\\ai小说生成器
  python diagnose.py --node-root ... --tag key_2001
  python diagnose.py --node-root ... --json
  python diagnose.py --list          # 列出全部已知故障模式

退出码：0=健康或仅提示，1=发现需处置的问题，2=诊断器自身无法运行
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
LOCAL_TZ = timezone(timedelta(hours=8))

# 与生产引擎同源的常量
WORKER_STALE_SECONDS = 120.0
SUCCESS_STATUSES = ("done", "recovered_success")
TERMINAL_STATUSES = ("done", "recovered_success", "failed")

# 连接类错误特征（熔断判定）
CONN_PATTERNS = (
    "cannot reach", "connection refused", "connection reset", "10061", "10060",
    "http 502", "http 503", "502 bad gateway", "503 service", "timeout",
    "timed out", "getaddrinfo failed", "remote end closed", "bad gateway",
)

# 资源门禁阈值（与 production_node/bootstrap.ps1 同源）
GATE_MIN_HEADROOM_GB = 6.0
GATE_NO_NEW_PCT = 90.0
GATE_STOP_PCT = 92.0
GATE_MIN_AVAIL_MB = 1024


# ---------------------------------------------------------------- 故障模式目录

FAILURE_MODES = {
    "FM-01": {
        "name": "commit 耗尽 / MemoryError",
        "symptoms": ["MemoryError", "WinError 1455", "页面文件不足",
                     "worker 异常退出", "commit >= 92%"],
        "judge": "宿主 commit 耗尽。生产整树通常仅占 0.4-0.5GB——元凶几乎总是"
                 "宿主其他进程（浏览器/桌面端/重复服务实例），不是生产线本身。",
        "action": "立即停止扩张（不新增线/worker）；已运行线按资源守卫只停不启；"
                  "清理宿主进程或重启机器释放 commit；确认 state.json 完好后再 resume。",
        "evidence_hint": "logs/<worker>.exception.json、GlobalMemoryStatusEx 读数",
    },
    "FM-02": {
        "name": "辅助进程重复实例占资源",
        "symptoms": ["启动前 commit 已很高", "多个同名 python 服务实例"],
        "judge": "机器上已有重复的服务实例在吃 commit，生产还没开始就处于危险区。",
        "action": "先清场再生产。门禁不放行就不启动——'先跑起来再说'是 FM-01 的直接成因。",
        "evidence_hint": "PowerShell CIM 进程表 + commit 读数",
    },
    "FM-03": {
        "name": "worker crash（done 不能丢）",
        "symptoms": ["worker 进程消失", "worker_exits.jsonl 有记录", "单元停在 claimed"],
        "judge": "worker 异常退出，在制单元停在 claimed。done 是终态，state 原子写"
                 "保证已完成篇目完好。",
        "action": "同 tag resume。stale claimed 由引擎回收（产物完整→recovered_success，"
                  "缺失→pending）。不要手工改 done。",
        "evidence_hint": "state.json 五态 + logs/worker_exits.jsonl",
    },
    "FM-04": {
        "name": "stale claimed 滞留",
        "symptoms": ["claimed > 0 但无存活 worker", "heartbeat 很旧"],
        "judge": "claimed 单元心跳停滞超过 worker_stale_seconds(120s) 且无 worker 存活。",
        "action": "resume（引擎启动时批量回收）。验收时 claimed != 0 一律不得判 COMPLETED。",
        "evidence_hint": "unit.heartbeat（float epoch 秒）与当前时间差",
    },
    "FM-05": {
        "name": "上游中断烧任务（拒连风暴）",
        "symptoms": ["大量 failed", "llm_calls.jsonl 尾部连续连接类错误",
                     "connection refused / 502 / 503 / timeout"],
        "judge": "上游不可达，每单元各自重试 3 次后 failed。客户端无熔断，"
                 "引擎层面挡不住这种模式。",
        "action": "熔断：停该线进程树 → PAUSED_UPSTREAM，pending 原样保留；"
                  "网关恢复（真实探测，非 /health）后同 tag resume。"
                  "failed 只能显式重试。",
        "evidence_hint": "llm_calls.jsonl 尾部连续连接类失败计数",
    },
    "FM-06": {
        "name": "Dashboard 状态漂移",
        "symptoms": ["面板数字与磁盘对不上", "completed/pending 口径混淆"],
        "judge": "面板有三个不同口径（completed=当前批次、活跃=300s 窗口、"
                 "待办=全库累计），极易混读。",
        "action": "一切以 state.json 五态 + 进程表双证据为准；汇报统一用 "
                  "status_lines.py 口径；不引用面板截图当验收。",
        "evidence_hint": "state.json vs /api/status 对比",
    },
    "FM-07": {
        "name": "completed-with-failures 误判",
        "symptoms": ["pending==0 被当成全部完成", "实际有 failed"],
        "judge": "完成判定必须五数齐全：done+recovered==target 且 failed==0 "
                 "且 claimed==0 且 pending==0。",
        "action": "判 COMPLETED_WITH_FAILURES / FAILED_WITH_RESULTS；"
                  "报告里失败数必须可见，不许含在成功里。",
        "evidence_hint": "state.json 五态计数",
    },
    "FM-08": {
        "name": "start API 假失败",
        "symptoms": ["启动接口 500", "但生产线其实已起来"],
        "judge": "spawn 先完成，之后的留痕步骤因 D 盘 OSError 失败。",
        "action": "先查进程表有没有该 tag 的进程、再查 state 是否推进；有则忽略 500。"
                  "不要因为 500 再启动一遍（会撞 FM-09）。",
        "evidence_hint": "进程表 + state.json mtime",
    },
    "FM-09": {
        "name": "同 tag 双启动",
        "symptoms": ["两个调度器跑一个 state", "文件锁争抢", "计数错乱"],
        "judge": "同 tag 已有存活进程时又启动了一次。",
        "action": "拒绝启动，走 resume。state 的 O_EXCL 锁是防损坏的最后一道墙，"
                  "不是并发调度器的设计载荷。",
        "evidence_hint": "进程表按 tag 匹配",
    },
    "FM-10": {
        "name": "断电 / D 盘闪断后 state 恢复",
        "symptoms": ["全树消失", "读写 state 时 OSError", "JSON 解析失败"],
        "judge": "state.json 是 tmp+os.replace 原子写的，断电通常无损；"
                 "读失败 != 数据坏（可能是 replace 瞬间或目录闪断）。",
        "action": "读按指数退避重试 >=4 次再判死；判死后停止扩张，只 resume。",
        "evidence_hint": "state.json 可解析性 + 单元计数完整性",
    },
    "FM-11": {
        "name": "网关 /health 假绿",
        "symptoms": ["/health 正常但请求 502"],
        "judge": "/health 不发网络调用，只证网关进程就绪。",
        "action": "用真实最小调用探测（node_check probe）；熔断恢复判定也用真实探测。",
        "evidence_hint": "node_check.py probe 结果",
    },
    "FM-12": {
        "name": "Key 与吞吐真相",
        "symptoms": ["加 worker 但吞吐不成比例"],
        "judge": "每单元 3 次串行 LLM 调用（plan/draft/critic）才是瓶颈；"
                 "总 worker >12 后收益边际极小。",
        "action": "想要更多产出时先加线（隔离/多样性），不是无脑加 worker。",
        "evidence_hint": "llm_calls.jsonl 的 stage 分布与耗时",
    },
}


# ---------------------------------------------------------------- 基础工具

def eprint(*a):
    print(*a, file=sys.stderr)


def read_json_retry(path: Path, attempts: int = 4):
    """容错读 JSON（D 盘闪断对策：指数退避重试）。"""
    delay = 0.15
    for i in range(attempts):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            if i == attempts - 1:
                return None
            time.sleep(delay)
            delay *= 2
    return None


def query_memory() -> dict | None:
    """Windows commit/物理内存。非 Windows 返回 None（诊断降级）。"""
    fake = os.environ.get("LIR_FAKE_MEMORY_JSON")
    if fake:
        return json.loads(fake)
    if not IS_WINDOWS:
        return None
    import ctypes
    import ctypes.wintypes as wt

    class MSX(ctypes.Structure):
        _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64)]

    st = MSX()
    st.dwLength = ctypes.sizeof(MSX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    gb = float(1024 ** 3)
    limit, avail = st.ullTotalPageFile / gb, st.ullAvailPageFile / gb
    used = max(0.0, limit - avail)
    return {"total_phys_gb": round(st.ullTotalPhys / gb, 2),
            "avail_phys_gb": round(st.ullAvailPhys / gb, 2),
            "commit_limit_gb": round(limit, 2),
            "commit_avail_gb": round(avail, 2),
            "commit_used_gb": round(used, 2),
            "commit_pct": round(used / limit * 100, 1) if limit else 0.0,
            "commit_headroom_gb": round(avail, 2)}


def list_python_processes() -> list:
    if not IS_WINDOWS:
        return []
    ps = ("Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
          "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30,
                             creationflags=CREATE_NO_WINDOW)
        data = json.loads(out.stdout or "null")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = [data]
    return [{"pid": int(d["ProcessId"]), "cmd": d.get("CommandLine") or ""}
            for d in (data or [])]


def is_conn_error(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in CONN_PATTERNS)


def runs_dir(node: Path) -> Path:
    return node / "data" / "multi_worker_generation" / "runs"


def find_run_dirs(node: Path, tag: str | None = None) -> list[Path]:
    base = runs_dir(node)
    if not base.is_dir():
        return []
    if tag:
        p = base / f"multi_worker_{tag}"
        return [p] if p.is_dir() else []
    return sorted([d for d in base.iterdir() if d.is_dir()], key=lambda d: d.name)


def state_of(run_dir: Path) -> dict | None:
    return read_json_retry(run_dir / "mw_pilot" / "state.json")


def counts_of(state: dict) -> dict:
    c = {s: 0 for s in ("pending", "claimed", "done", "failed", "recovered_success")}
    for u in state.get("units", []):
        st = u.get("status")
        c[st] = c.get(st, 0) + 1
    c["total"] = len(state.get("units", []))
    return c


# ---------------------------------------------------------------- 检查项

def check_memory() -> dict:
    m = query_memory()
    if m is None:
        return {"id": "memory", "level": "UNKNOWN",
                "detail": "无法查询内存（非 Windows 或 API 失败）", "memory": None}
    pct, head, avail_mb = m["commit_pct"], m["commit_headroom_gb"], m["avail_phys_gb"] * 1024
    if pct >= GATE_STOP_PCT or avail_mb < GATE_MIN_AVAIL_MB:
        return {"id": "memory", "level": "CRITICAL", "memory": m,
                "detail": f"commit {pct}% 或可用物理 {avail_mb:.0f}MB 触及停止线",
                "mode": "FM-01",
                "action": "只停不启；清理宿主进程或重启释放 commit"}
    if head < GATE_MIN_HEADROOM_GB:
        return {"id": "memory", "level": "BLOCK", "memory": m,
                "detail": f"commit headroom {head}GB < {GATE_MIN_HEADROOM_GB}GB",
                "mode": "FM-01", "action": "禁止新增生产线"}
    if pct >= GATE_NO_NEW_PCT:
        return {"id": "memory", "level": "CAUTION", "memory": m,
                "detail": f"commit {pct}% >= {GATE_NO_NEW_PCT}%",
                "mode": "FM-01", "action": "不启动新 worker"}
    return {"id": "memory", "level": "OK", "memory": m,
            "detail": f"commit {pct}%（headroom {head}GB），可用物理 {m['avail_phys_gb']}GB"}


def check_worker_exceptions(run_dir: Path) -> dict:
    """扫描 worker 异常现场（FM-01 / FM-03 的硬证据）。"""
    logs = run_dir / "logs"
    if not logs.is_dir():
        return {"id": "worker_exceptions", "level": "OK", "detail": "无 logs 目录",
                "exceptions": []}
    excs = []
    for p in sorted(logs.glob("*.exception.json")):
        doc = read_json_retry(p)
        text = json.dumps(doc, ensure_ascii=False) if doc else p.read_text(
            encoding="utf-8", errors="replace")
        excs.append({"file": p.name, "text": text[:400],
                     "memory_error": "MemoryError" in text or "1455" in text})
    if not excs:
        return {"id": "worker_exceptions", "level": "OK",
                "detail": "无 worker 异常文件", "exceptions": []}
    mem = [e for e in excs if e["memory_error"]]
    if mem:
        return {"id": "worker_exceptions", "level": "CRITICAL", "exceptions": excs,
                "detail": f"{len(mem)} 个 worker 异常含 MemoryError/1455", "mode": "FM-01",
                "action": "commit 耗尽；停止扩张，释放宿主内存后 resume"}
    return {"id": "worker_exceptions", "level": "WARN", "exceptions": excs,
            "detail": f"{len(excs)} 个 worker 异常文件（非内存类）", "mode": "FM-03",
            "action": "检查异常内容；done 是终态不会丢，同 tag resume 续跑"}


def check_unit_states(run_dir: Path, tag: str) -> dict:
    """五态完整性 + stale claimed（FM-04 / FM-07）。"""
    state = state_of(run_dir)
    if state is None:
        return {"id": "unit_states", "level": "UNKNOWN", "tag": tag,
                "detail": "state.json 缺失或不可读（FM-10：重试后仍失败需人工确认）",
                "mode": "FM-10"}
    c = counts_of(state)
    now = time.time()
    stale = []
    for u in state.get("units", []):
        if u.get("status") != "claimed":
            continue
        hb = u.get("heartbeat")
        if not isinstance(hb, (int, float)) or (now - hb) > WORKER_STALE_SECONDS:
            stale.append(u.get("unit_id"))
    target = state.get("size") or c["total"]
    success = c["done"] + c["recovered_success"]
    if c["pending"] == 0 and c["claimed"] == 0:
        if c["failed"] == 0 and success == target:
            judged = "COMPLETED"
        elif success + c["failed"] >= target:
            judged = ("COMPLETED_WITH_FAILURES" if success >= max(1, target // 2)
                      else "FAILED_WITH_RESULTS")
        else:
            judged = "INCOMPLETE"
    else:
        judged = "IN_PROGRESS"
    level = "OK"
    mode = None
    detail = f"{judged}：done {c['done']} + recovered {c['recovered_success']} / {target}，" \
             f"failed {c['failed']}，claimed {c['claimed']}，pending {c['pending']}"
    action = None
    if stale:
        level, mode = "WARN", "FM-04"
        detail += f"；{len(stale)} 个 stale claimed"
        action = "resume 时引擎会回收（产物完整→recovered_success，缺失→pending）"
    if c["failed"] > 0:
        level = "WARN" if level == "OK" else level
        mode = mode or "FM-07"
        action = (action or "") + " failed 是终态，不静默重试；需显式 retry 或接受带失败完成"
    return {"id": "unit_states", "level": level, "tag": tag, "counts": c,
            "judged": judged, "stale_claimed": stale, "detail": detail,
            "mode": mode, "action": action, "state": state}


def check_breaker(run_dir: Path) -> dict:
    """熔断判定（FM-05）：llm_calls.jsonl 尾部连续连接类失败。"""
    p = run_dir / "llm_calls.jsonl"
    if not p.exists():
        return {"id": "breaker", "level": "UNKNOWN",
                "detail": "无 llm_calls.jsonl（未启用 --meter 或尚未调用）"}
    try:
        size = p.stat().st_size
        with open(p, "rb") as f:
            if size > 262144:
                f.seek(-262144, os.SEEK_END)
            text = f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return {"id": "breaker", "level": "UNKNOWN", "detail": f"读取失败：{e}"}
    recs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not recs:
        return {"id": "breaker", "level": "UNKNOWN", "detail": "计量文件为空"}
    total = len(recs)
    errs = [r for r in recs if r.get("ok") is False]
    conn = [r for r in errs if is_conn_error(str(r.get("error", "")))]
    streak = 0
    for r in reversed(recs):
        if r.get("ok") is False and is_conn_error(str(r.get("error", ""))):
            streak += 1
        else:
            break
    if streak >= 6:
        return {"id": "breaker", "level": "CRITICAL", "mode": "FM-05",
                "detail": f"尾部连续 {streak} 条连接类失败（窗口内 {total} 条，"
                          f"错误 {len(errs)}，其中连接类 {len(conn)}）",
                "action": "熔断：停该线进程树 → PAUSED_UPSTREAM；"
                          "网关真实探测恢复后同 tag resume"}
    if conn:
        return {"id": "breaker", "level": "WARN",
                "detail": f"窗口内 {len(conn)} 条连接类失败（尾部连续 {streak}，未达阈值 6）",
                "action": "观察；若持续增长则准备熔断"}
    return {"id": "breaker", "level": "OK",
            "detail": f"窗口内 {total} 条调用，错误 {len(errs)}，无连接类失败"}


def check_double_launch(node: Path, tag: str, run_dir: Path) -> dict:
    """同 tag 双启动检测（FM-09）。"""
    procs = list_python_processes()
    if not procs:
        return {"id": "double_launch", "level": "UNKNOWN", "detail": "无法获取进程表"}
    rd = str(run_dir).lower()
    tag_arg = f"--tag {tag}".lower()
    mains, workers = [], []
    for p in procs:
        cmd = (p.get("cmd") or "").lower()
        if "run.py" in cmd and "multi_worker_generation" in cmd and tag_arg in cmd:
            mains.append(p["pid"])
        elif "worker.py" in cmd and rd in cmd:
            workers.append(p["pid"])
    if len(mains) > 1:
        return {"id": "double_launch", "level": "CRITICAL", "mode": "FM-09",
                "detail": f"检测到 {len(mains)} 个同 tag 调度进程：{mains}",
                "action": "立即停止多余实例（只保留一个），否则 state 计数会错乱"}
    return {"id": "double_launch", "level": "OK",
            "detail": f"调度进程 {len(mains)} 个，worker {len(workers)} 个"
                      + (f"（pids {mains} / {workers}）" if mains or workers else "")}


def check_artifacts(run_dir: Path, state: dict | None) -> dict:
    """产物一致性（FM-03 / FM-07）：done 单元必须有完整产物。"""
    if state is None:
        return {"id": "artifacts", "level": "UNKNOWN", "detail": "无 state，跳过核对"}
    works = run_dir / "mw_pilot" / "works"
    missing, ok = [], 0
    for u in state.get("units", []):
        if u.get("status") not in SUCCESS_STATUSES:
            continue
        uid = u.get("unit_id", "")
        wdir = works / uid
        content, meta = wdir / "content.md", wdir / "metadata.json"
        good = False
        if content.exists() and meta.exists():
            try:
                if content.stat().st_size > 0:
                    m = json.loads(meta.read_text(encoding="utf-8"))
                    good = (m.get("unit_id") == uid
                            and str(m.get("work_id", "")).startswith("work_"))
            except (OSError, json.JSONDecodeError):
                good = False
        if good:
            ok += 1
        else:
            missing.append(uid)
    if missing:
        return {"id": "artifacts", "level": "CRITICAL", "mode": "FM-07",
                "detail": f"{len(missing)} 个成功单元缺产物（例：{missing[:3]}）",
                "action": "不得判 COMPLETED；用 --recover-only 尝试产物恢复，"
                          "或人工核对后显式重试"}
    return {"id": "artifacts", "level": "OK",
            "detail": f"{ok} 个成功单元产物完整"}


# ---------------------------------------------------------------- 主流程

def diagnose(node: Path, tag: str | None) -> dict:
    checks = [check_memory()]
    targets = find_run_dirs(node, tag)
    if not targets:
        checks.append({"id": "runs", "level": "UNKNOWN",
                       "detail": f"未找到运行目录（{runs_dir(node)}）"
                                 + (f"，tag={tag}" if tag else "")})
        return {"node_root": str(node), "tag": tag, "checks": checks,
                "generated_at": datetime.now(LOCAL_TZ).isoformat(timespec="seconds")}

    for rd in targets[-3:]:  # 最多看最近 3 个 run
        t = rd.name.replace("multi_worker_", "")
        state = state_of(rd)
        for c in (check_unit_states(rd, t), check_worker_exceptions(rd),
                  check_breaker(rd), check_artifacts(rd, state),
                  check_double_launch(node, t, rd)):
            c["tag"] = t          # 多批次同屏时必须能区分归属
            checks.append(c)

    return {"node_root": str(node), "tag": tag, "checks": checks,
            "generated_at": datetime.now(LOCAL_TZ).isoformat(timespec="seconds")}


def render(result: dict) -> int:
    order = {"CRITICAL": 0, "BLOCK": 1, "WARN": 2, "CAUTION": 3, "UNKNOWN": 4, "OK": 5}
    checks = sorted(result["checks"], key=lambda c: order.get(c["level"], 9))
    # UNKNOWN 表示"证据不足"，不是故障；只有 CRITICAL/BLOCK/WARN/CAUTION 参与定级。
    # 若全部为 OK/UNKNOWN，结论为 OK（并在下方列出证据缺口）。
    known = [c for c in checks if c["level"] != "UNKNOWN"]
    worst = min((order.get(c["level"], 9) for c in known), default=5)
    gaps = [c for c in checks if c["level"] == "UNKNOWN"]
    print("=" * 68)
    print("  Literary Lab 事故诊断")
    print("=" * 68)
    print(f"  Node: {result['node_root']}")
    if result.get("tag"):
        print(f"  Tag : {result['tag']}")
    print(f"  时间: {result['generated_at']}")
    print()
    for c in checks:
        icon = {"CRITICAL": "!!", "BLOCK": " !", "WARN": " ?", "CAUTION": " ?",
                "UNKNOWN": " .", "OK": " +"}.get(c["level"], " ?")
        who = f"{c['tag']} " if c.get("tag") else ""
        print(f"[{icon}] {who}{c['id']:<18} {c['level']:<9} {c.get('detail', '')}")
        if c.get("mode"):
            fm = FAILURE_MODES.get(c["mode"], {})
            print(f"      → {c['mode']} {fm.get('name', '')}")
            print(f"        判断：{fm.get('judge', '')}")
        if c.get("action"):
            print(f"        动作：{c['action']}")
        if c.get("stale_claimed"):
            print(f"        stale claimed: {c['stale_claimed'][:5]}")
    print()
    verdict = {0: "CRITICAL — 需立即处置", 1: "BLOCK — 禁止扩张",
               2: "WARN — 需关注", 3: "CAUTION — 谨慎", 4: "UNKNOWN — 证据不足",
               5: "OK — 未发现已知故障模式"}[worst]
    print(f"  结论：{verdict}")
    if gaps:
        print(f"  证据缺口（{len(gaps)} 项，非故障）：")
        for g in gaps[:5]:
            who = f"{g['tag']} " if g.get("tag") else ""
            print(f"    - {who}{g['id']}: {g.get('detail', '')}")
    print("=" * 68)
    return 0 if worst >= 4 else 1


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Literary Lab 事故诊断器（只读）")
    ap.add_argument("--node-root", default=os.environ.get("LITERARYLAB_NODE_ROOT"),
                    help="Production Node 根目录（默认取 LITERARYLAB_NODE_ROOT）")
    ap.add_argument("--tag", default=None, help="只诊断该 tag")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true", help="列出全部已知故障模式")
    args = ap.parse_args()

    if args.list:
        for k, v in FAILURE_MODES.items():
            print(f"{k}  {v['name']}")
            print(f"     症状：{'、'.join(v['symptoms'])}")
            print(f"     判断：{v['judge']}")
            print(f"     动作：{v['action']}")
            print()
        return 0

    if not args.node_root:
        eprint("需要 --node-root 或环境变量 LITERARYLAB_NODE_ROOT")
        return 2
    node = Path(args.node_root)
    if not (node / "experiments" / "multi_worker_generation" / "run.py").exists():
        eprint(f"不是有效的 Production Node：{node}")
        return 2

    result = diagnose(node, args.tag)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    return render(result)


if __name__ == "__main__":
    raise SystemExit(main())
