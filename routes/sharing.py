from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from bson import ObjectId
from config import get_database

# Explicitly defining the router
router = APIRouter(prefix="/api/sharing", tags=["sharing"])

@router.post("/share")
async def share_file(request: Request):
    """Placeholder to test import"""
    return {"message": "router found!"}