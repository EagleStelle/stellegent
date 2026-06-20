"""Audit log (admin only)."""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends

from ...db import list_audit
from ...deps import require_roles

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=List[dict])
def audit_log(_u: dict = Depends(require_roles("admin"))):
    return [dict(r) for r in list_audit()]
