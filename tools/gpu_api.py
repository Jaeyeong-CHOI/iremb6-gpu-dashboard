#!/usr/bin/env python3
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI(title="iREMB GPU API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def run(cmd):
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return p.stdout.strip()

@app.get('/metrics')
def metrics(node: str = Query(...)):
    q = "nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
    out = run(f"ssh {node} \"{q}\"")
    gpus = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(',')]
        if len(parts) >= 5:
            gpus.append({
                'index': int(parts[0]),
                'name': parts[1],
                'util': int(parts[2]),
                'mem_used': int(parts[3]),
                'mem_total': int(parts[4]),
            })
    return {'node': node, 'gpus': gpus}
