# Setup (Windows 11)
1) Install Java 17, Node 18+, Python 3.11+, Git.
2) Start gateway:
```powershell
cd bot-gateway
npm i
npm run dev
```
3) Start orchestrator:
```powershell
cd orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs and call /health and /step.