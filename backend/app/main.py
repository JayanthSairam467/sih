"""
Sagar Rakshak — AI-fused Satellite-AIS Maritime Pollution Attribution & Response Platform
FastAPI backend for SIH26143 (NTRO)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import detection, ais, drift, attribution, demo

app = FastAPI(
    title="Sagar Rakshak",
    description="Satellite-AIS Maritime Pollution Attribution & Response Platform — SIH26143",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detection.router, prefix="/api/detection", tags=["Detection"])
app.include_router(ais.router, prefix="/api/ais", tags=["AIS"])
app.include_router(drift.router, prefix="/api/drift", tags=["Drift"])
app.include_router(attribution.router, prefix="/api/attribution", tags=["Attribution"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sagar-rakshak"}
