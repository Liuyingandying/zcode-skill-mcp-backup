#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""night-fiction-factory：共享原语库（纯标准库，零第三方依赖）。

本模块只做编排层的"事实来源"工作，不实现任何生成逻辑：
  - 发现 Production Node（LITERARYLAB_NODE_ROOT / 上次成功使用的提示文件）
  - 读写 night_registry.json（原子写 + 重试读，吸取 D 盘闪断教训）
  - 读取生产线 state.json 五态计数（pending/claimed/done/failed/recovered_success）
  - Windows commit/物理内存门禁（GlobalMemoryStatusEx，不依赖 psutil）
  - 进程发现/匹配/安全杀树（PowerShell CIM + taskkill /F /T，绝不按映像名杀）
  - 网络熔断判定（llm_calls.jsonl 尾部连续连接类失败）
  - 完成判定（严禁 pending==0 即 completed）

所有会触碰外部世界的函数保持小而可注入，供 tests/ 打桩。
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

SKILL_NAME = "night-fiction-factory"
SKILL_VERSION = "1.0"

IS_WINDOWS = platform.system() == "Windows"
DETACHED = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
CREATE_NO_WINDOW = 0x08000000

# 与生产引擎一致的 tag 校验（dashboard/control.py：^[A-Za-z0-9_\-]{1,64}$）
TAG_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

# state.json unit 五态（scheduler.py / recovery.py 的精确拼写）
UNIT_STATUSES = ("pending", "claimed", "done", "failed", "recovered_success")
SUCCESS_STATUSES = ("done", "recovered_success")

# 生产线状态机（Skill 层）
LINE_STATUSES = (
    "PLANNED", "RUNNING", "PAUSED_UPSTREAM", "PAUSED_RESOURCE",
    "STOPPED", "FAILED_RESUMABLE",
    "COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS",
)
FINAL_LINE_STATUSES = ("COMPLETED", "COMPLETED_WITH_FAILURES", "FAILED_WITH_RESULTS")

# 连接类错误特征（小写子串匹配；熔断只在"结尾连续命中且无成功"时触发）
CONNECTION_ERROR_PATTERNS = (
    "cannot reach", "connection refused", "connection reset", "connectionreset",
    "10061", "10060", "http 502", "http 503", "502 bad gateway",
    "503 service", "timeout", "timed out", "getaddrinfo failed",
    "temporary failure in name resolution", "remote end closed",
    "bad gateway",
)

# 资源门禁阈值（与 production_node/bootstrap.ps1、pilot-100.ps1 同源）
GATE_MIN_HEADROOM_GB = 6.0     # commit headroom 低于此值：禁止新增生产线（FAIL 级）
GATE_NO_NEW_COMMIT_PCT = 90.0  # commit >= 90%：不启动新 worker
GATE_STOP_COMMIT_PCT = 92.0    # commit >= 92%：暂停/停止继续扩张（只停不自动重启）
GATE_MIN_AVAIL_MB = 1024       # 可用物理内存低于此值：等同 CRITICAL

BREAKER_WINDOW = 12            # 检查 llm_calls.jsonl 尾部多少条
BREAKER_THRESHOLD = 6          # 连续多少条连接类失败判熔断

WORKER_STALE_SECONDS = 120.0   # 与引擎 config.json worker_stale_seconds 同源


# ---------------------------------------------------------------- 基础工具

def eprint(*args):
    print(*args, file=sys.stderr)


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_stop_at(s: str, now: datetime | None = None) -> datetime:
    """'08:00' → 今天（已过则明天）的 08:00 本地时间。"""
    now = now or datetime.now()
    h, m = s.split(":")
    target = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


# 常见题材 → tag slug（tag 只允许 ASCII，引擎正则 ^[A-Za-z0-9_\-]{1,64}$）
GENRE_SLUG_MAP = {
    "科幻": "scifi", "悬疑": "mystery", "都市": "urban", "奇幻": "fantasy",
    "童话": "fairy", "乡土": "rural", "散文": "essay", "诗歌": "poetry",
    "短篇": "story", "武侠": "wuxia", "言情": "romance", "历史": "history",
    "恐怖": "horror", "推理": "detective", "儿童": "children", "mixed": "mixed",
}


def sanitize_slug(s: str) -> str:
    import hashlib
    s = s.strip()
    if s in GENRE_SLUG_MAP:
        return GENRE_SLUG_MAP[s]
    slug = re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()
    if not slug:
        # 非 ASCII（中文等）且不在映射表：取稳定哈希前缀，保证同名题材同名 slug
        slug = "g" + hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]
    return slug


def fmt_gb(x) -> str:
    return f"{x:.1f}"


# ---------------------------------------------------------------- 状态目录与注册簿

def state_dir() -> Path:
    env = os.environ.get("NFF_STATE_DIR")
    return Path(env).expanduser() if env else Path.home() / ".night-fiction-factory"


def registry_path() -> Path:
    return state_dir() / "night_registry.json"


def plans_dir() -> Path:
    return state_dir() / "plans"


def logs_dir() -> Path:
    return state_dir() / "logs"


def reports_dir() -> Path:
    return state_dir() / "reports"


def samples_path(plan_id: str) -> Path:
    return state_dir() / "samples" / f"{plan_id}.jsonl"


def audit_log(msg: str) -> None:
    try:
        p = state_dir() / "audit.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{iso_now()} {msg}\n")
    except OSError:
        pass


def new_registry() -> dict:
    return {"version": 1, "updated_at": iso_now(), "plans": {}}


def load_registry() -> dict:
    p = registry_path()
    reg = load_json_retry(p)
    if not isinstance(reg, dict) or "plans" not in reg:
        return new_registry()
    return reg


def save_registry(reg: dict) -> None:
    reg["updated_at"] = iso_now()
    atomic_write_text(registry_path(), json.dumps(reg, ensure_ascii=False, indent=2))


def get_plan(reg: dict, plan_id: str) -> dict | None:
    return reg.get("plans", {}).get(plan_id)


# ---------------------------------------------------------------- 原子读写（D 盘闪断对策）

def atomic_write_text(path: Path, text: str, attempts: int = 4) -> None:
    """tmp + flush + fsync + os.replace，OSError 指数退避重试。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    delay = 0.2
    for i in range(attempts):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return
        except OSError:
            if i == attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass


def load_json_retry(path: Path, attempts: int = 5) -> object | None:
    path = Path(path)
    delay = 0.15
    for i in range(attempts):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            if i == attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2
    return None


# ---------------------------------------------------------------- Production Node 发现

def _node_marker_ok(root: Path) -> bool:
    root = Path(root)
    return ((root / "experiments" / "multi_worker_generation" / "run.py").exists()
            and (root / "ops" / "lab_control.py").exists())


def find_node_root() -> tuple["Path | None", str]:
    """返回 (node_root, message)。禁止硬编码工程路径。"""
    env = os.environ.get("LITERARYLAB_NODE_ROOT")
    if env:
        p = Path(env).expanduser()
        if _node_marker_ok(p):
            _remember_node_root(p)
            return p, "LITERARYLAB_NODE_ROOT"
        return None, (f"LITERARYLAB_NODE_ROOT={env} 不是有效的 Production Node"
                      f"（缺少 experiments/multi_worker_generation/run.py 或 ops/lab_control.py）")
    hint = state_dir() / "node_root.txt"
    if hint.exists():
        try:
            p = Path(hint.read_text(encoding="utf-8").strip())
            if _node_marker_ok(p):
                return p, "hint"
        except OSError:
            pass
    return None, ("未找到 Production Node。请设置环境变量 LITERARYLAB_NODE_ROOT 指向工程根"
                  "（其下应存在 experiments/multi_worker_generation/run.py 与 ops/lab_control.py）。"
                  "Skill 不硬编码任何工程路径。")


def _remember_node_root(root: Path) -> None:
    try:
        hint = state_dir() / "node_root.txt"
        hint.parent.mkdir(parents=True, exist_ok=True)
        old = hint.read_text(encoding="utf-8").strip() if hint.exists() else ""
        if old != str(root):
            hint.write_text(str(root), encoding="utf-8")
    except OSError:
        pass


def run_dir_for(root: Path, tag: str) -> Path:
    return Path(root) / "data" / "multi_worker_generation" / "runs" / f"multi_worker_{tag}"


def state_path_for(root: Path, tag: str) -> Path:
    return run_dir_for(root, tag) / "mw_pilot" / "state.json"


# ---------------------------------------------------------------- state 五态

def counts_from_units(units: list) -> dict:
    c = {s: 0 for s in UNIT_STATUSES}
    c["total"] = len(units)
    for u in units:
        st = u.get("status")
        c[st] = c.get(st, 0) + 1
    return c


def success_count(counts: dict) -> int:
    return counts.get("done", 0) + counts.get("recovered_success", 0)


def read_state(root: Path, tag: str) -> dict | None:
    p = state_path_for(root, tag)
    if not p.exists():
        return None
    return load_json_retry(p)


def read_state_counts(root: Path, tag: str) -> tuple[dict | None, dict | None]:
    state = read_state(root, tag)
    if state is None:
        return None, None
    return state, counts_from_units(state.get("units", []))


def stale_claimed(units: list, stale_seconds: float = WORKER_STALE_SECONDS,
                  now: float | None = None) -> list:
    """heartbeat 缺失或超过 stale_seconds 的 claimed 单元。"""
    now = now if now is not None else time.time()
    out = []
    for u in units:
        if u.get("status") != "claimed":
            continue
        hb = u.get("heartbeat")
        if not isinstance(hb, (int, float)) or (now - hb) > stale_seconds:
            out.append(u)
    return out


def artifact_ok(run_dir: Path, unit_id: str) -> bool:
    """核对 done 单元在磁盘上是否真有产物（recovery.artifact_of 的简化镜像）。"""
    wdir = Path(run_dir) / "mw_pilot" / "works" / unit_id
    meta, content = wdir / "metadata.json", wdir / "content.md"
    if not meta.exists() or not content.exists():
        return False
    try:
        if content.stat().st_size <= 0:
            return False
        m = json.loads(meta.read_text(encoding="utf-8"))
        return m.get("unit_id") == unit_id and str(m.get("work_id", "")).startswith("work_")
    except (OSError, json.JSONDecodeError):
        return False


# ---------------------------------------------------------------- 完成判定（核心规则）

def judge_counts(counts: dict, target: int, success_floor: float = 0.5) -> str:
    """严禁 pending==0 即 completed。

    COMPLETED                  : done+recovered == target 且 failed==0 且 claimed==0 且 pending==0
    COMPLETED_WITH_FAILURES    : 全部终态、有失败、成功率 >= success_floor
    FAILED_WITH_RESULTS        : 全部终态、有失败、成功率 <  success_floor
    IN_PROGRESS                : 尚有 pending/claimed
    """
    done = success_count(counts)
    failed = counts.get("failed", 0)
    pending = counts.get("pending", 0)
    claimed = counts.get("claimed", 0)
    if pending == 0 and claimed == 0:
        if failed == 0 and done == target:
            return "COMPLETED"
        if done + failed >= target:
            floor_n = max(1, math.ceil(target * success_floor))
            return "COMPLETED_WITH_FAILURES" if done >= floor_n else "FAILED_WITH_RESULTS"
    return "IN_PROGRESS"


def effective_line_status(reg_status: str, judged: str, live: int) -> str:
    """把 注册簿状态 / 判定 / 进程存活 三证据合成对外展示状态。"""
    if live > 0:
        return "RUNNING"
    if judged in FINAL_LINE_STATUSES:
        return judged
    if reg_status == "PLANNED":
        return "PLANNED"
    if reg_status in ("STOPPED", "PAUSED_UPSTREAM", "PAUSED_RESOURCE"):
        return reg_status
    if judged == "IN_PROGRESS":
        return "FAILED_RESUMABLE"
    return reg_status or "UNKNOWN"


# ---------------------------------------------------------------- 启动分类（防同 tag 双启动）

def classify_launch(run_dir: "Path | None", state: dict | None, live: int,
                    target: int) -> str:
    """fresh / completed / already_running / resumable / block_leftover"""
    if run_dir is None or not Path(run_dir).exists():
        return "fresh"
    if state is None:
        return "block_leftover"   # run 目录存在但没有 state.json → 拒绝，人工处理
    judged = judge_counts(counts_from_units(state.get("units", [])), target)
    if judged in FINAL_LINE_STATUSES:
        return "completed"
    if live > 0:
        return "already_running"
    return "resumable"


# ---------------------------------------------------------------- 资源门禁与 worker 预算

def memory_worker_cap(memory: dict, reserve_gb: float = 2.0,
                      workers_per_gb: float = 8.0) -> int:
    """经验公式：预留 reserve_gb commit 余量，其余每 GB 允许约 8 个 worker
    （实测 9 worker 整树 commit 仅 ~0.4-0.5GB，此公式留 2 倍以上余量）。"""
    usable = max(0.0, memory.get("commit_avail_gb", 0.0) - reserve_gb)
    return int(usable * workers_per_gb)


def allocate_workers(n_lines: int, max_total: int, memory: dict | None = None,
                     per_line_cap: int = 9) -> tuple[list, int]:
    """把总预算摊到各线（round-robin），绝不允许 N线×9。预算耗尽的线保持 PLANNED。"""
    budget = max_total
    if memory is not None:
        budget = min(budget, max(0, memory_worker_cap(memory)))
    base, rem = divmod(budget, n_lines)
    alloc = [min(per_line_cap, base + (1 if i < rem else 0)) for i in range(n_lines)]
    return alloc, budget


def evaluate_gate(memory: dict, min_headroom_gb: float = GATE_MIN_HEADROOM_GB,
                  no_new_pct: float = GATE_NO_NEW_COMMIT_PCT,
                  stop_pct: float = GATE_STOP_COMMIT_PCT,
                  min_avail_mb: float = GATE_MIN_AVAIL_MB) -> dict:
    """OK / CAUTION(不启动新 worker) / CRITICAL(只停不启) / BLOCK(禁止新增线)。

    "禁新增"（headroom BLOCK）与"停运行"（commit CRITICAL）是正交判定：
    两者同时成立时 level 记 CRITICAL，但两个动作都必须生效。
    """
    reasons: list = []
    headroom = memory.get("commit_headroom_gb", 0.0)
    pct = memory.get("commit_pct", 0.0)
    avail_mb = memory.get("avail_phys_gb", 0.0) * 1024

    block = headroom < min_headroom_gb
    stop = (pct >= stop_pct) or (avail_mb < min_avail_mb)
    caution = pct >= no_new_pct

    if block:
        reasons.append(f"commit headroom {headroom:.1f}GB < {min_headroom_gb}GB：禁止新增生产线")
    if stop:
        reasons.append(f"commit {pct:.1f}% 或可用物理 {avail_mb:.0f}MB 触及停止线："
                       f"只停不启（key_2001 语义）")
    elif caution:
        reasons.append(f"commit {pct:.1f}% >= {no_new_pct}%：不启动新 worker")

    if stop:
        level = "CRITICAL"
    elif block:
        level = "BLOCK"
    elif caution:
        level = "CAUTION"
    else:
        level = "OK"
    return {"level": level,
            "allow_new_line": not (block or stop or caution),
            "stop_running": stop,
            "reasons": reasons,
            "memory": memory}


def query_memory() -> dict:
    """Windows commit/物理内存（GB）。commit 取 GlobalMemoryStatusEx 的 PageFile 语义
    （= commit limit / avail，与 bootstrap.ps1 的 Get-CimInstance 口径一致）。

    测试注入口：环境变量 NFF_FAKE_MEMORY_JSON（query_memory 返回值的 JSON）。
    仅供 tests/ 与集成冒烟使用，生产脚本永不设置它。
    """
    fake = os.environ.get("NFF_FAKE_MEMORY_JSON")
    if fake:
        return json.loads(fake)
    if not IS_WINDOWS:
        raise OSError("query_memory 仅支持 Windows；非 Windows 请注入假内存状态")
    import ctypes
    import ctypes.wintypes as wt

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64)]

    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        raise OSError("GlobalMemoryStatusEx failed")
    gb = float(1024 ** 3)
    commit_limit = st.ullTotalPageFile / gb
    commit_avail = st.ullAvailPageFile / gb
    commit_used = max(0.0, commit_limit - commit_avail)
    return {"mem_load_pct": st.dwMemoryLoad,
            "total_phys_gb": round(st.ullTotalPhys / gb, 2),
            "avail_phys_gb": round(st.ullAvailPhys / gb, 2),
            "commit_limit_gb": round(commit_limit, 2),
            "commit_avail_gb": round(commit_avail, 2),
            "commit_used_gb": round(commit_used, 2),
            "commit_pct": round(commit_used / commit_limit * 100, 1) if commit_limit > 0 else 0.0,
            "commit_headroom_gb": round(commit_avail, 2)}


# ---------------------------------------------------------------- 进程（Windows 专用口径）

def list_python_processes(timeout: int = 30) -> list:
    """单行 PowerShell CIM（Win11 无 wmic；不经 shell 解析，CREATE_NO_WINDOW）。"""
    if not IS_WINDOWS:
        raise OSError("list_python_processes 仅支持 Windows")
    ps = ("Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
          "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=timeout,
                         creationflags=CREATE_NO_WINDOW)
    data = json.loads(out.stdout or "null")
    if isinstance(data, dict):
        data = [data]
    return [{"pid": int(d["ProcessId"]), "cmd": d.get("CommandLine") or ""}
            for d in (data or [])]


def match_line_pids(procs: list, tag: str, run_dir: "Path | None") -> list:
    """主 run.py 按 --tag 匹配；worker.py 无 --tag，按 run 目录路径匹配。"""
    rd = str(Path(run_dir)).lower() if run_dir else None
    tag_arg = f"--tag {tag}".lower()
    out = set()
    for p in procs or []:
        cmd = (p.get("cmd") or "").lower()
        if "run.py" in cmd and "multi_worker_generation" in cmd and tag_arg in cmd:
            out.add(p["pid"])
        elif rd and "worker.py" in cmd and rd in cmd:
            out.add(p["pid"])
    return sorted(out)


def kill_tree(pid: int, *, source: str | None = None, tag: str | None = None,
              reason: str = "", node_root: Path | None = None) -> bool:
    if source:
        try:
            root = node_root or find_node_root()[0]
            if root:
                if str(root) not in sys.path:
                    sys.path.insert(0, str(root))
                from ops.production_control_audit import record_stop_intent
                record_stop_intent(source=source, target_pid=pid, tag=tag,
                                   reason=reason)
        except (ImportError, OSError, ValueError):
            pass  # Audit failure must not change the existing stop behavior.
    r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True)
    return r.returncode == 0


def spawn_detached(args: list, cwd: Path, log_path: Path) -> int:
    """DETACHED 后台启动（lab_control.spawn_detached 同范式）：
    stdin=DEVNULL、输出追加到日志、close_fds、子进程强制 UTF-8。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_path, "ab", buffering=0)
    try:
        proc = subprocess.Popen(args, cwd=str(cwd), env=env,
                                stdin=subprocess.DEVNULL, stdout=fh,
                                stderr=subprocess.STDOUT,
                                creationflags=DETACHED if IS_WINDOWS else 0,
                                close_fds=True)
    finally:
        fh.close()
    return proc.pid


# ---------------------------------------------------------------- 熔断（网络 Circuit Breaker）

def is_connection_error(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in CONNECTION_ERROR_PATTERNS)


def read_text_tail(path: Path, max_bytes: int = 262144) -> str:
    path = Path(path)
    if not path.exists():
        return ""
    size = path.stat().st_size
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(-max_bytes, os.SEEK_END)
        return f.read().decode("utf-8", errors="replace")


def read_llm_tail(run_dir: Path, n: int = 400) -> list:
    text = read_text_tail(Path(run_dir) / "llm_calls.jsonl")
    recs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return recs[-n:]


def breaker_verdict(records: list, threshold: int = BREAKER_THRESHOLD) -> dict:
    """records 按时间升序（llm_calls.jsonl 尾部即升序）。
    结尾 threshold 条全部是连接类失败 → OUTAGE。"""
    if len(records) < threshold:
        return {"state": "UNKNOWN", "consecutive": 0, "reason": "样本不足"}
    hits = 0
    last_err = ""
    for r in reversed(records):
        if r.get("ok") is False and is_connection_error(str(r.get("error", ""))):
            hits += 1
            last_err = str(r.get("error", ""))[:200]
            if hits >= threshold:
                break
        else:
            break
    if hits >= threshold:
        return {"state": "OUTAGE", "consecutive": hits, "reason": last_err}
    return {"state": "HEALTHY", "consecutive": hits, "reason": ""}


def breaker_from_state(units: list, threshold: int = BREAKER_THRESHOLD) -> dict:
    """无 llm_calls.jsonl 时的降级判定：按 state 列表尾部的 failed 单元
    中连接类错误的连续命中计数（启发式，弱于计量口径）。"""
    fails = [u for u in units if u.get("status") == "failed"][-threshold:]
    hits = 0
    for u in reversed(fails):
        if is_connection_error(str(u.get("error", ""))):
            hits += 1
        else:
            break
    if hits >= threshold:
        return {"state": "OUTAGE", "consecutive": hits,
                "reason": str(fails[-1].get("error", ""))[:200]}
    return {"state": "HEALTHY" if fails else "UNKNOWN", "consecutive": hits, "reason": ""}


# ---------------------------------------------------------------- Resume / Stop 纯逻辑

def rewrite_failed_to_pending(state: dict) -> int:
    """显式 retry_failed：failed → pending（attempts 清零、清占用痕迹）。
    调用方必须先备份 state.json 并写审计日志——禁止静默篡改。"""
    n = 0
    for u in state.get("units", []):
        if u.get("status") == "failed":
            u["status"] = "pending"
            u["attempts"] = 0
            for k in ("worker", "claimed_at", "heartbeat", "error"):
                u.pop(k, None)
            n += 1
    return n


def build_stop_plan(plan: dict, only_lines: list | None, procs: list) -> dict:
    """只允许停本 NightPlan 自己拥有、且进程表能对上 tag/run_dir 的进程树。"""
    kills, skipped = [], []
    for lid, line in sorted(plan.get("lines", {}).items()):
        if only_lines and lid not in only_lines:
            continue
        if line.get("status") in FINAL_LINE_STATUSES:
            skipped.append({"line_id": lid, "reason": f"已是终态 {line.get('status')}"})
            continue
        pids = set(match_line_pids(procs, line["tag"], line.get("run_dir")))
        reg_pid = line.get("pid")
        if reg_pid:
            hit = [p for p in procs or [] if p["pid"] == reg_pid]
            if hit and match_line_pids(hit, line["tag"], line.get("run_dir")):
                pids.add(reg_pid)
            elif not hit:
                skipped.append({"line_id": lid,
                                "reason": f"登记 PID {reg_pid} 已不在进程表（可能已退出）"})
            else:
                skipped.append({"line_id": lid,
                                "reason": f"登记 PID {reg_pid} 命令行与 tag 不匹配（疑似 PID 复用），拒绝误杀"})
        if pids:
            kills.append({"line_id": lid, "tag": line["tag"], "pids": sorted(pids)})
        elif not any(s["line_id"] == lid for s in skipped):
            skipped.append({"line_id": lid, "reason": "无存活进程"})
    return {"kills": kills, "skipped": skipped}


# ---------------------------------------------------------------- Provider Profile（只存环境变量名，绝不含 Key 值）

PROVIDERS = {
    "glm": {
        "base_url_env": "NFF_GLM_API_BASE", "base_url_default": "http://127.0.0.1:8000/v1",
        "model_env": "NFF_GLM_MODEL", "model_default": "",
        "key_env_name_env": "NFF_GLM_KEY_ENV", "key_env_name_default": "TJULLM_API_KEY_1",
        "timeout_env": "NFF_GLM_TIMEOUT", "timeout_default": "120",
        "max_concurrency_env": "NFF_GLM_MAX_CONCURRENCY", "max_concurrency_default": "12",
    },
    "tju": {
        "base_url_env": "NFF_TJU_API_BASE", "base_url_default": "http://127.0.0.1:8000/v1",
        "model_env": "NFF_TJU_MODEL", "model_default": "",
        "key_env_name_env": "NFF_TJU_KEY_ENV", "key_env_name_default": "TJULLM_API_KEY_1",
        "timeout_env": "NFF_TJU_TIMEOUT", "timeout_default": "120",
        "max_concurrency_env": "NFF_TJU_MAX_CONCURRENCY", "max_concurrency_default": "9",
    },
    "custom_openai_compatible": {
        "base_url_env": "NFF_CUSTOM_API_BASE", "base_url_default": "",
        "model_env": "NFF_CUSTOM_MODEL", "model_default": "",
        "key_env_name_env": "NFF_CUSTOM_KEY_ENV", "key_env_name_default": "",
        "timeout_env": "NFF_CUSTOM_TIMEOUT", "timeout_default": "120",
        "max_concurrency_env": "NFF_CUSTOM_MAX_CONCURRENCY", "max_concurrency_default": "8",
    },
}


def resolve_provider(name: str) -> dict:
    prof = PROVIDERS.get(name)
    if prof is None:
        raise SystemExit(f"未知 provider: {name}（可选：{', '.join(PROVIDERS)}）")

    def pick(env_key, default):
        return os.environ.get(env_key) or default

    return {"name": name,
            "base_url": pick(prof["base_url_env"], prof["base_url_default"]),
            "model": pick(prof["model_env"], prof["model_default"]),
            "key_env_name": pick(prof["key_env_name_env"], prof["key_env_name_default"]),
            "timeout_s": int(pick(prof["timeout_env"], prof["timeout_default"]) or 120),
            "max_concurrency": int(pick(prof["max_concurrency_env"],
                                        prof["max_concurrency_default"]) or 8)}


def probe_provider(base_url: str, timeout: float = 3.0) -> dict:
    """网络层探测：只测 TCP 可达。/health 存在假绿（不证上游可用），
    真实探测需 node_check.py probe（真实最小 LLM 调用）。"""
    if not base_url:
        return {"tcp": None, "host": "", "port": 0, "reason": "未配置 base_url"}
    u = urllib.parse.urlparse(base_url)
    host, port = u.hostname or "127.0.0.1", u.port or (443 if u.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"tcp": True, "host": host, "port": port}
    except OSError as e:
        return {"tcp": False, "host": host, "port": port, "reason": str(e)}


# ---------------------------------------------------------------- 晨间报告

def build_report(plan: dict, line_details: list, runtime_seconds: float,
                 peaks: dict, extra_notes: list | None = None) -> str:
    started = plan.get("created_at", "?")
    total_target = sum(l["target"] for l in line_details)
    total_done = sum(l["done"] for l in line_details)
    total_failed = sum(l["failed"] for l in line_details)
    total_recovered = sum(l.get("recovered_success", 0) for l in line_details)
    lines_md = ["| LINE | DONE | FAILED | RECOVERED | TARGET | 状态 | 说明 |",
                "|---|---|---|---|---|---|---|"]
    for l in line_details:
        lines_md.append(
            f"| {l['line_id']} | {l['done']} | {l['failed']} | "
            f"{l.get('recovered_success', 0)} | {l['target']} | {l['status']} | "
            f"{(l.get('note') or '').replace('|', '/')} |")
    hours = runtime_seconds / 3600.0
    md = f"""# NIGHT_PRODUCTION_REPORT

- 计划：{plan.get('plan_id')}（provider={plan.get('provider')}，stop_at={plan.get('stop_at')}）
- 计划开始：{started}　实际运行：{hours:.2f} 小时
- **计划目标 {total_target} 篇 / 实际成功 {total_done} 篇**（含产物恢复 {total_recovered}）
- 失败 {total_failed} 篇　失败单元处置：{'FAILED_UNITS_REQUIRE_EXPLICIT_RETRY（未自动重试）' if total_failed else '无'}

## 各生产线

{chr(10).join(lines_md)}

## 资源与异常

- commit 峰值：{peaks.get('max_commit_used_gb', '?')} GB / {peaks.get('commit_limit_gb', '?')} GB
- 可用物理内存最低：{peaks.get('min_avail_phys_gb', '?')} GB
- 资源门禁触发次数：{peaks.get('gate_trips', 0)}；网络熔断触发次数：{peaks.get('breaker_trips', 0)}
"""
    if extra_notes:
        md += "\n## 备注\n\n" + "\n".join(f"- {n}" for n in extra_notes) + "\n"
    md += "\n##作品目录\n\n"
    for l in line_details:
        md += f"- {l['line_id']}（{l['tag']}）：`{l.get('run_dir') or '?'}/mw_pilot/works/`\n"
    return md


def reconfigure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
