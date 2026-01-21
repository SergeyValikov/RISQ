from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

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
    contract_type: str = ""
    analysis_date: date = Field(default_factory=date.today)
    pages: int = 0
    overall_status: OverallStatus = "Низкий уровень внимания"


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
    cover: Cover = Field(default_factory=Cover)

    # было conlist(5..7) — для MVP лучше не валить всё, если LLM вернул меньше
    summary: list[str] = Field(default_factory=list)

    risk_map: list = Field(default_factory=list)
    atypical: list = Field(default_factory=list)
    contradictions: list = Field(default_factory=list)

    duties_balance: dict = Field(default_factory=dict)
    needs_specialist: list = Field(default_factory=list)
    missing_sections: list = Field(default_factory=list)

    disclaimer: str = "Отчёт сформирован автоматически и не является юридической консультацией."
