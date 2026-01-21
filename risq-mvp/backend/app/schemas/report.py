from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, conlist


OverallStatus = Literal[
    "Низкий уровень внимания",
    "Средний уровень внимания",
    "Повышенное внимание",
]

RiskCategory = Literal[
    "ответственность",
    "сроки",
    "оплата",
    "расторжение",
    "конфиденциальность",
]

MissingSection = Literal[
    "форс-мажор",
    "ответственность",
    "порядок расторжения",
]


class Cover(BaseModel):
    contract_type: str
    analysis_date: date
    pages: int
    overall_status: OverallStatus


class RiskItem(BaseModel):
    category: RiskCategory
    description: str
    clause_ref: str


class AtypicalItem(BaseModel):
    quote: str
    note: str


class ContradictionItem(BaseModel):
    description: str
    clause_refs: list[str]


class DutiesBalance(BaseModel):
    customer_count: int
    provider_count: int
    note: str


class SpecialistItem(BaseModel):
    item: str
    clause_ref: str


class Report(BaseModel):
    cover: Cover
    summary: conlist(str, min_length=5, max_length=7)
    risk_map: list[RiskItem]
    atypical: list[AtypicalItem]
    contradictions: list[ContradictionItem]
    duties_balance: DutiesBalance
    needs_specialist: list[SpecialistItem]
    missing_sections: list[MissingSection]
    disclaimer: Literal[
        "Отчёт сформирован автоматически и не является юридической консультацией."
    ] = Field(
        "Отчёт сформирован автоматически и не является юридической консультацией."
    )
