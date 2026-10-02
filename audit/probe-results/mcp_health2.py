# -*- coding: utf-8 -*-
"""MCP health check v2: sequential init -> initialized -> tools/list per server.
Records time-to-init and time-to-tools + tool counts. Read-only."""
import json, os, subprocess, time, threading, urllib.request, shutil, queue

CFG = r"C:\Users\FAJ\.zcode\cli\config.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_health2.json")
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "zcode-audit", "version": "1.0"}}}
INITED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LISTTOOLS = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

def readline_q(q, p, timeout):
    try: return q.get(timeout=timeout)
    except queue.Empty: return None

def check_stdio(name, cfg, timeout):
    cmd = cfg.get("command"); args = cfg.get("args", [])
    exe = shutil.which(cmd) or cmd
    env = dict(os.environ); env.update(cfg.get("env", {}))
    t0 = time.time()
    res = {"name": name, "kind": "stdio", "cmd": f"{cmd} {' '.join(args)[:90]}"}
    try:
        p = subprocess.Popen([exe] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        res.update(ok=False, error=f"spawn failed: {e}"); return res
    q = queue.Queue()
    def reader():
        try:
            for line in iter(p.stdout.readline, b""):
                q.put(line)
        except Exception: pass
    threading.Thread(target=reader, daemon=True).start()
    try:
        p.stdin.write((json.dumps(INIT) + "\n").encode()); p.stdin.flush()
    except Exception as e:
        res.update(ok=False, error=f"stdin: {e}"); p.kill(); return res
    line = readline_q(q, p, timeout)
    if line is None:
        res.update(ok=False, error="no initialize response (timeout)")
        try: p.kill()
        except Exception: pass
        return res
    res["init_ms"] = int((time.time() - t0) * 1000)
    si = {}
    try:
        d = json.loads(line.decode("utf-8", "replace"))
        si = d.get("result", {}).get("serverInfo", {})
    except Exception: pass
    res["server_info"] = f"{si.get('name','?')} {si.get('version','')}".strip()
    try:
        p.stdin.write((json.dumps(INITED) + "\n").encode())
        p.stdin.write((json.dumps(LISTTOOLS) + "\n").encode()); p.stdin.flush()
    except Exception as e:
        res.update(ok=True, error=f"tools/list write failed: {e}")
        try: p.kill()
        except Exception: pass
        return res
    t1 = time.time()
    while True:
        line = readline_q(q, p, max(10, timeout - (time.time() - t0)))
        if line is None: break
        try:
            d = json.loads(line.decode("utf-8", "replace"))
            if d.get("id") == 2:
                res["tool_count"] = len(d.get("result", {}).get("tools", []))
                res["tools_ms"] = int((t1 - t0) * 1000)
                break
        except Exception: continue
    res["ok"] = res.get("tool_count") is not None
    try: p.kill()
    except Exception: pass
    return res

def check_http(name, cfg, timeout):
    t0 = time.time(); res = {"name": name, "kind": "http", "url_host": cfg.get("url", "")[:45]}
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               **cfg.get("headers", {})}
    try:
        req = urllib.request.Request(cfg["url"], data=json.dumps(INIT).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        res["init_ms"] = int((time.time() - t0) * 1000)
        if body.startswith("event:") or "\n data:" in body or body.startswith("data:"):
            for ln in body.splitlines():
                if ln.startswith("data:"):
                    d = json.loads(ln[5:].strip()); break
        else:
            d = json.loads(body)
        si = d.get("result", {}).get("serverInfo", {})
        res["server_info"] = f"{si.get('name','?')} {si.get('version','')}".strip()
        res["ok"] = d.get("result") is not None
        sid = r.headers.get("mcp-session-id")
        if d.get("result") is not None:
            if sid: headers["mcp-session-id"] = sid
            req2 = urllib.request.Request(cfg["url"], data=json.dumps(LISTTOOLS).encode(), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req2, timeout=60) as r2:
                    b2 = r2.read().decode("utf-8", "replace")
                for ln in ([b2] if not (b2.startswith("event:") or b2.startswith("data:")) else b2.splitlines()):
                    if ln.startswith("data:"):
                        d2 = json.loads(ln[5:].strip())
                        if d2.get("id") == 2:
                            res["tool_count"] = len(d2.get("result", {}).get("tools", []))
            except Exception as e:
                res["tools_error"] = repr(e)[:120]
    except Exception as e:
        res["init_ms"] = int((time.time() - t0) * 1000)
        res.update(ok=False, error=repr(e)[:160])
    return res

def main():
    cfg = json.load(open(CFG, encoding="utf-8"))
    servers = cfg["mcp"]["servers"]
    results, threads, lock = [], [], threading.Lock()
    def run(name, scfg):
        timeout = min(scfg.get("timeoutMs", 90000) / 1000, 300)
        r = check_http(name, scfg, timeout) if ("url" in scfg or scfg.get("type") == "http") else check_stdio(name, scfg, timeout)
        with lock: results.append(r)
        print(f"[done] {name}: ok={r.get('ok')} init={r.get('init_ms')}ms tools={r.get('tool_count')} {r.get('error','')}", flush=True)
    for name, scfg in servers.items():
        t = threading.Thread(target=run, args=(name, scfg), daemon=True)
        t.start(); threads.append(t)
    for t in threads: t.join(360)
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("WROTE", OUT)

if __name__ == "__main__":
    main()
