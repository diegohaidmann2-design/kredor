"""Verificações extras (code review) do endpoint GET /api/analise/clientes"""
import os
import re
from pathlib import Path

import requests
from dotenv import dotenv_values

env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or env["REACT_APP_BACKEND_URL"]).rstrip("/")
content = Path("/app/memory/test_credentials.md").read_text()
email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)
senha = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?senha(?:\*\*)?\s*:\s*`?([^`\s]+)', content).group(1)

s = requests.Session()
tok = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "senha": senha}).json()["access_token"]
s.headers.update({"Authorization": f"Bearer {tok}"})

r = s.get(f"{BASE_URL}/api/analise/clientes?limit=100", timeout=120)
cl = r.json()["clientes"]
ult = {c["ultimo_pagamento"] for c in cl}
print("clientes:", len(cl))
print("valores distintos de ultimo_pagamento:", len(ult), list(ult)[:3])

rc = s.get(f"{BASE_URL}/api/clientes?limit=200", timeout=120)
body = rc.json()
items = body.get("items") if isinstance(body, dict) else body
print("GET /api/clientes total:", len(items or []))
sem_score = [c.get("nome") for c in (items or []) if c.get("score_atual") is None]
print("clientes sem score_atual:", len(sem_score), sem_score[:5])

# dashboard
rd = s.get(f"{BASE_URL}/api/analise/dashboard?periodo=30d", timeout=120)
print("dashboard", rd.status_code, rd.json() if rd.status_code == 200 else rd.text[:200])
