"""Schemas del módulo `health`. Conforme a `contracts/health.openapi.yaml`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

DependencyState = Literal["up", "down"]


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    db: DependencyState
    storage: DependencyState
    version: str
