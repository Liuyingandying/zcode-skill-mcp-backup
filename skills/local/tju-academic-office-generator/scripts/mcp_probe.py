#!/usr/bin/env python3
"""MCP 服务器探针：启动指定 stdio MCP 服务器，完成 initialize 握手并拉取工具清单。

用法:
    python mcp_probe.py --command uvx --arg "--from" --arg office-word-mcp-server --arg word_mcp_server
    python mcp_probe.py --config mcp_servers.json   # 批量探测配置文件里的所有服务器

配置文件格式（与 ZCode mcp.servers 一致）:
    {"word-document-server": {"command": "uvx", "args": ["..."], "env": {}}}

输出: 每个服务器一行 JSON: {"name":..., "ok": true/false, "tool_count": N, "tools": [...], "error": "..."}
退出码: 全部成功 0，任一失败 1。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import queue
import os

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2024-11-05", "capabilities": {},
    "clientInfo": {"name": "skill-probe", "version": "1.0"}}}
INITED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LIST_TOOLS = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}


def probe(name: str, command: str, args: list[str], env: dict | None = None, timeout: float = 120.0) -> dict:
    result = {"name": name, "ok": False, "tool_count": 0, "tools": [], "error": None}
    proc_env = os.environ.copy()
    proc_env.update(env or {})
    try:
        proc = subprocess.Popen([command, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=proc_env, text=True, encoding="utf-8")
    except OSError as exc:
        result["error"] = f"无法启动 {command!r}: {exc}"
        return result

    replies: queue.Queue[dict] = queue.Queue()

    def reader(stream, sink: queue.Queue):
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                sink.put(json.loads(line))
            except json.JSONDecodeError:
                pass  # 忽略非 JSON 噪声（部分服务器会往 stdout 打日志）
        sink.put({"__eof__": True})

    threading.Thread(target=reader, args=(proc.stdout, replies), daemon=True).start()
    # stderr 单独排空，防止缓冲区写满阻塞
    threading.Thread(target=lambda: [None for _ in proc.stderr], daemon=True).start()

    def send(msg: dict):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def wait_for(msg_id: int) -> dict | None:
        import time
        deadline = time.time() + timeout
        pending: list[dict] = []
        while time.time() < deadline:
            try:
                msg = replies.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                break
            if msg.get("__eof__"):
                break
            if msg.get("id") == msg_id:
                return msg
            pending.append(msg)
        return None

    try:
        send(INIT)
        init_resp = wait_for(1)
        if not init_resp or "result" not in init_resp:
            result["error"] = f"initialize 握手失败: {json.dumps(init_resp, ensure_ascii=False)[:300] if init_resp else '超时/进程退出'}"
            return result
        send(INITED)
        send(LIST_TOOLS)
        tools_resp = wait_for(2)
        if not tools_resp or "result" not in tools_resp:
            result["error"] = "tools/list 失败或超时"
            return result
        tools = tools_resp["result"].get("tools", [])
        result.update(ok=True, tool_count=len(tools),
                      tools=[t.get("name", "?") for t in tools])
        return result
    finally:
        try:
            proc.kill()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command")
    parser.add_argument("--arg", action="append", default=[])
    parser.add_argument("--config")
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="单服务器超时秒数；首次 uvx 运行需要下载包，建议 ≥180")
    ns = parser.parse_args()

    targets: list[tuple[str, dict]] = []
    if ns.config:
        with open(ns.config, encoding="utf-8") as fh:
            for name, spec in json.load(fh).items():
                targets.append((name, spec))
    elif ns.command:
        targets.append((ns.command, {"command": ns.command, "args": ns.arg}))
    else:
        parser.error("需要 --command 或 --config")

    all_ok = True
    for name, spec in targets:
        r = probe(name, spec["command"], spec.get("args", []), spec.get("env"), ns.timeout)
        all_ok &= r["ok"]
        print(json.dumps(r, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
