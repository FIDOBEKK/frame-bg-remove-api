#!/usr/bin/env python3
"""
Simple background-removal API using rembg + FastAPI.

Security:
- Requires API token in header:
  - Authorization: Bearer <token>
  OR
  - X-API-Token: <token>
"""

from __future__ import annotations

import os
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from rembg import remove

MAX_BYTES = int(os.getenv("BG_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
API_TOKEN = os.getenv("BG_API_TOKEN", "")

app = FastAPI(title="Background Removal API", version="1.0.0")


def _verify_token(authorization: str | None, x_api_token: str | None) -> None:
    if not API_TOKEN:
        raise HTTPException(status_code=500, detail="Server not configured: BG_API_TOKEN missing")

    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()

    token = bearer or (x_api_token or "").strip()

    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.post("/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
) -> Response:
    _verify_token(authorization, x_api_token)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_BYTES} bytes)")

    try:
        out = remove(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Background removal failed: {exc}")

    return Response(content=out, media_type="image/png")
