from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ReportCover(BaseModel):
    contract_type: str
    analysis_date: str
    overall_status: str

    # Для PDF
    pages: Optional[int] = None

    # Для DOCX / общего объёма
    chars: Optional[int] = None
    words: Optional[int] = None


class RiskItem(BaseModel):
    category: str
    description: str
    clause_ref: Optional[str] = None


class AtypicalItem(BaseModel):
    quote: Optional[str] = None
    note: str


class ContradictionItem(BaseModel):
    description: str
    clause_refs: List[str] = []


class DutiesBalance(BaseModel):
    customer_count: int
    provider_count: int
    note: Optional[str] = None


class SpecialistItem(BaseModel):
    item: str
    clause_ref: Optional[str] = None


class Report(BaseModel):
    cover: ReportCover
    summary: List[str] = []
    risk_map: List[RiskItem] = []
    atypical: List[AtypicalItem] = []
    contradictions: List[ContradictionItem] = []
    duties_balance: DutiesBalance
    needs_specialist: List[SpecialistItem] = []
    missing_sections: List[str] = []
    disclaimer: Optional[str] = None

