#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess, shlex, threading, time
from collections import defaultdict, deque

DEFAULT_NODES = ["iREMB-C-03", "iREMB-C-07"]
SAMPLE_SEC = 0.5
WINDOW_SEC = 60
MAX_POINTS = int(WINDOW_SEC / SAMPLE_SEC)

app = FastAPI(title="iREMB GPU API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# HISTORY[node][gpu_index] = deque([{ts, util, mem_used, mem_total, name}], maxlen=60)
HISTORY = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_POINTS)))
LOCK = threading.Lock()


def run(cmd: str, timeout: int = 8) -> str:
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "command failed").strip())
    return p.stdout.strip()


def collect_node(node: str) -> dict:
    safe_node = shlex.quote(node)
    q = "nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
    out = run(f"ssh -o BatchMode=yes -o ConnectTimeout=3 {safe_node} \"{q}\"")

    gpus = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(',')]
        if len(parts) >= 5:
            gpus.append({
                "index": int(parts[0]),
                "name": parts[1],
                "util": int(parts[2]),
                "mem_used": int(parts[3]),
                "mem_total": int(parts[4]),
            })
    return {"node": node, "gpus": gpus}


def sampler_loop():
    while True:
        now = int(time.time())
        for node in DEFAULT_NODES:
            try:
                data = collect_node(node)
                with LOCK:
                    for g in data.get("gpus", []):
                        HISTORY[node][g["index"]].append({
                            "ts": now,
                            "util": g["util"],
                            "mem_used": g["mem_used"],
                            "mem_total": g["mem_total"],
                            "name": g["name"],
                        })
            except Exception:
                # Keep running even if one node temporarily fails.
                pass
        time.sleep(SAMPLE_SEC)


@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=sampler_loop, daemon=True)
    t.start()


@app.get("/health")
def health():
    return {"ok": True, "nodes": DEFAULT_NODES, "sample_sec": SAMPLE_SEC, "window_sec": WINDOW_SEC}


@app.get("/metrics")
def metrics(node: str = Query(...)):
    try:
        return collect_node(node)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{node}: {e}")


@app.get("/metrics/all")
def metrics_all():
    out = []
    for n in DEFAULT_NODES:
        try:
            out.append(collect_node(n))
        except Exception as e:
            out.append({"node": n, "error": str(e), "gpus": []})
    return {"nodes": out}


@app.get("/history")
def history(node: str = Query(...)):
    with LOCK:
        node_data = HISTORY.get(node, {})
        gpus = []
        for gpu_index, dq in node_data.items():
            points = list(dq)
            if not points:
                continue
            latest = points[-1]
            gpus.append({
                "index": gpu_index,
                "name": latest.get("name", "unknown"),
                "latest": {
                    "util": latest.get("util", 0),
                    "mem_used": latest.get("mem_used", 0),
                    "mem_total": latest.get("mem_total", 0),
                },
                "points": points,
            })
    return {"node": node, "window_sec": WINDOW_SEC, "sample_sec": SAMPLE_SEC, "gpus": gpus}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tools.gpu_api:app", host="0.0.0.0", port=8088, reload=False)
