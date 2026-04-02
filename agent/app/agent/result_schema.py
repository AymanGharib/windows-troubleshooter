"""
Pydantic schemas for troubleshooter agent output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    category: str
    probable_cause: str
    reasoning: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    source: str
    detail: str


class RecommendedRemediation(BaseModel):
    action: str
    command: str | None = None
    explanation: str


class TroubleshootingResult(BaseModel):
    status: Literal["COMPLETED", "NEEDS_INFO", "FAILED"]
    mode: Literal["troubleshoot"] = "troubleshoot"
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    diagnosis: Diagnosis
    evidence_used: list[EvidenceItem] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_remediation: RecommendedRemediation
    needs_human: bool = True
