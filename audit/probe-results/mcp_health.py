# -*- coding: utf-8 -*-
"""Read-only MCP health check: initialize + tools/list handshake per server.
No destructive tool calls. Results written to mcp_health.json"""
import json, os, subprocess, sys, time, threading, urllib.request, shutil

CFG = r"C:\Users\FAJ\.zcode\cli\config.json"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_health.json")
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "zcode-audit", "version": "1.0"}}}
INITED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LISTTOOLS = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

def check_stdio(name, cfg, timeout):
    cmd = cfg.get("command"); args = cfg.get("args", [])
    exe = shutil.which(cmd) or cmd
    env = dict(os.environ); env.update(cfg.get("env", {}))
    t0 = time.time()
    res = {"name": name, "kind": "stdio", "cmd": f"{cmd} {' '.join(args)[:100]}"}
    try:
        p = subprocess.Popen([exe] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        res.update(ok=False, error=f"spawn failed: {e}"); return res
    state = {"init": None, "tools": None, "err": b""}
    def reader():
        try:
            state["init"] = p.stdout.readline()
            p.stdin.write((json.dumps(INITED) + "\n").encode()); p.stdin.flush()
            state["tools"] = p.stdout.readline()
        except Exception as e:
            state["err"] = str(e).encode()
    th = threading.Thread(target=reader, daemon=True); th.start()
    try:
        p.stdin.write((json.dumps(INIT) + "\n").encode()); p.stdin.flush()
    except Exception as e:
        res.update(ok=False, error=f"stdin write failed: {e}")
        p.kill(); return res
    th.join(timeout)
    res["elapsed_ms"] = int((time.time() - t0) * 1000)
    if state["init"] is None:
        err = p.stderr.read(400) if p.poll() is not None else b"timeout"
        res.update(ok=False, error=f"no init response: {state['err'] or err[:200]}")
    else:
        try:
            toolcount = None; server_info = ""
            if state["tools"] and state["tools"].strip():
                d = json.loads(state["tools"].decode("utf-8", "replace"))
                toolcount = len(d.get("result", {}).get("tools", []))
            try:
                id1 = json.loads(state["init"].decode("utf-8", "replace"))
                si = id1.get("result", {}).get("serverInfo", {})
                server_info = f"{si.get('name','?')} {si.get('version','')}".strip()
            except Exception: pass
            res.update(ok=True, tool_count=toolcount, server_info=server_info)
        except Exception as e:
            res.update(ok=False, error=f"parse: {e}")
    try: p.kill()
    except Exception: pass
    return res

def check_http(name, cfg, timeout):
    t0 = time.time(); res = {"name": name, "kind": "http", "url_host": cfg.get("url", "")[:40]}
    req = urllib.request.Request(cfg["url"], data=json.dumps(INIT).encode(),
        headers={"Content-Type": "application/json", **cfg.get("headers", {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            res["elapsed_ms"] = int((time.time() - t0) * 1000)
            d = json.loads(body.decode("utf-8", "replace"))
            si = d.get("result", {}).get("serverInfo", {})
            res.update(ok=d.get("result") is not None,
                       server_info=f"{si.get('name','?')} {si.get('version','')}".strip(),
                       error=None if d.get("result") is not None else str(d)[:200])
    except Exception as e:
        res["elapsed_ms"] = int((time.time() - t0) * 1000)
        res.update(ok=False, error=repr(e)[:200])
    return res

def main():
    cfg = json.load(open(CFG, encoding="utf-8"))
    servers = cfg["mcp"]["servers"]
    results = []
    threads = []
    lock = threading.Lock()
    def run(name, scfg):
        timeout = min(scfg.get("timeoutMs", 120000) / 1000, 240)
        if scfg.get("type") == "http" or "url" in scfg:
            r = check_http(name, scfg, timeout)
        else:
            r = check_stdio(name, scfg, timeout)
        with lock: results.append(r)
        print(f"[done] {name}: ok={r.get('ok')} {r.get('elapsed_ms','?')}ms tools={r.get('tool_count')}", flush=True)
    for name, scfg in servers.items():
        t = threading.Thread(target=run, args=(name, scfg), daemon=True)
        t.start(); threads.append(t)
    for t in threads: t.join(300)
    json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("WROTE", OUT)

if __name__ == "__main__":
    main()
