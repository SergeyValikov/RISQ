from __future__ import annotations

import os

from openai import OpenAI
from pydantic import ValidationError

from backend.app.schemas.report import Report

SYSTEM_PROMPT = (
    "Ты формируешь автоматический предварительный отчёт по договору. "
    "\nЗапрещено: рекомендации (\"следует\", \"рекомендуется\"), "
    "оценка законности (\"незаконно\", \"нарушает\"), "
    "выводы о выгоде/невыгоде."
    "\nРазрешено: нейтральные наблюдения (\"обратите внимание\", "
    "\"может содержать риск\", \"требует дополнительной проверки\", "
    "\"отсутствует раздел\")."
    "\nВсегда возвращай ТОЛЬКО валидный JSON строго по заданной схеме, "
    "без Markdown, без комментариев, без лишних полей."
    "\nЕсли данных недостаточно, заполняй поля нейтрально, clause_ref ставь \"—\", "
    "списки могут быть пустыми (кроме summary: 5–7 пунктов)."
)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан")
    return OpenAI(api_key=api_key)


def _build_user_message(contract_type: str, text: str, pages: int) -> str:
    return (
        f"Тип договора: {contract_type}\n"
        f"Страниц: {pages}\n"
        "Текст договора (обрезан до 200k символов):\n"
        f"{text}"
    )


def _validate_report(payload: str) -> Report:
    return Report.model_validate_json(payload)


def analyze_contract(contract_type: str, text: str, pages: int) -> Report:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = _client()
    user_message = _build_user_message(contract_type, text, pages)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""

    try:
        return _validate_report(content)
    except ValidationError:
        retry_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Исправь JSON строго по схеме, без лишних полей. "
                        "Верни только валидный JSON.\n\n" + content
                    ),
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        retry_content = retry_response.choices[0].message.content or ""
        return _validate_report(retry_content)
