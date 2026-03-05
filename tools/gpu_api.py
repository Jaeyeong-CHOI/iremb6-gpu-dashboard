#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import shlex

DEFAULT_NODES = ["iREMB-C-03", "iREMB-C-07"]

app = FastAPI(title="iREMB GPU API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
            gpus.append(
                {
                    "index": int(parts[0]),
                    "name": parts[1],
                    "util": int(parts[2]),
                    "mem_used": int(parts[3]),
                    "mem_total": int(parts[4]),
                }
            )
    return {"node": node, "gpus": gpus}


@app.get("/health")
def health():
    return {"ok": True, "nodes": DEFAULT_NODES}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tools.gpu_api:app", host="0.0.0.0", port=8088, reload=False)
