"""
api/main.py — واجهة FastAPI.
المالك: لجين (الخلفية/التكامل).

تشغيل:  uvicorn mutawassim.api.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from ..schemas import Post, ResponseCard
from ..pipeline import run_pipeline

app = FastAPI(title="MUTAWASSIM API", version="0.1.0")


class VerifyRequest(BaseModel):
    posts: list[Post]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/verify", response_model=list[ResponseCard])
def verify_batch(req: VerifyRequest) -> list[ResponseCard]:
    raw = [p.model_dump() for p in req.posts]
    return run_pipeline(raw)
