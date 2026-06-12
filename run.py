"""IPInsight Agent OS 서버 실행 진입점"""
import sys
import os

# smart_farm 경로가 sys.path에 있으면 제거 (충돌 방지)
sys.path = [p for p in sys.path if "smart_farm" not in p.replace("\\", "/")]
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8100, reload=True)
