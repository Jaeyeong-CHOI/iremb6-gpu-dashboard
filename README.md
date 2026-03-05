# iREMB GPU Dashboard (Public)

2개 노드(iREMB-C-03, iREMB-C-07)의 GPU 사용량을 웹으로 보여주는 대시보드입니다.

## 구성
- `docs/06-gpu-dashboard.html`: 정적 대시보드 UI
- `tools/gpu_api.py`: FastAPI 메트릭 API (`/metrics?node=...`)
- `.github/workflows/pages.yml`: GitHub Pages 배포 워크플로우

## API 실행
```bash
pip install fastapi uvicorn
python tools/gpu_api.py
# 또는
python -m uvicorn tools.gpu_api:app --host 0.0.0.0 --port 8088
```

체크:
```bash
curl http://127.0.0.1:8088/health
curl "http://127.0.0.1:8088/metrics?node=iREMB-C-03"
curl "http://127.0.0.1:8088/metrics/all"
curl "http://127.0.0.1:8088/history?node=iREMB-C-03"
```

- `/history`는 최근 1분(5초 간격) 데이터를 서버가 계속 수집해 제공합니다.
- 브라우저를 닫아도 서버 수집은 계속됩니다(API 프로세스가 살아있는 동안).

## 대시보드
Pages 배포 후:
- `/06-gpu-dashboard.html`

기본 API 주소는 `http://127.0.0.1:8088` 입니다.
