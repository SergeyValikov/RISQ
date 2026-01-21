from __future__ import annotations

import os
from datetime import date

from openai import OpenAI
from pydantic import ValidationError

from backend.app.schemas.report import Report

SYSTEM_PROMPT = (
    "Ты формируешь автоматический предварительный отчёт по договору оказания услуг. "
    "Сервис НЕ является юридической консультацией.\n\n"
    "Запрещено:\n"
    "- рекомендации (\"следует\", \"рекомендуется\", \"нужно сделать\")\n"
    "- оценка законности (\"незаконно\", \"нарушает\")\n"
    "- выводы о выгоде/невыгоде\n\n"
    "Разрешено:\n"
    "- нейтральные наблюдения (\"обратите внимание\", \"может содержать риск\", "
    "\"требует дополнительной проверки\", \"отсутствует раздел\")\n\n"
    "Формат ответа: ТОЛЬКО валидный JSON. Без Markdown. Без комментариев. Без лишних полей.\n"
)

# Жёсткий шаблон ответа: модель должна заполнить поля внутри этой структуры
JSON_TEMPLATE_EXAMPLE = """{
  "cover": {
    "contract_type": "Договор оказания услуг",
    "analysis_date": "2026-01-21",
    "pages": 2,
    "overall_status": "Средний уровень внимания"
  },
  "summary": [
    "Обратите внимание на сроки оказания услуг и порядок согласования этапов.",
    "Может содержать риск из-за отсутствия/неясности порядка приёмки результата.",
    "Уточните условия оплаты (сроки, основания для удержаний, штрафы).",
    "Проверьте условия ответственности и ограничения ответственности сторон.",
    "Обратите внимание на условия расторжения и сроки уведомления."
  ],
  "risk_map": [
    {
      "category": "сроки",
      "description": "Сроки выполнения сформулированы неоднозначно, может потребоваться уточнение механизма продления/переноса.",
      "clause_ref": "п. —"
    }
  ],
  "atypical": [
    {
      "quote": "Исполнитель вправе изменять условия оказания услуг в одностороннем порядке…",
      "note": "Нетипично: одностороннее изменение условий может требовать дополнительной проверки."
    }
  ],
  "contradictions": [
    {
      "description": "В разных пунктах указаны разные сроки оплаты (например, 5 и 10 рабочих дней).",
      "clause_refs": ["п. —", "п. —"]
    }
  ],
  "duties_balance": {
    "customer_count": 0,
    "provider_count": 0,
    "note": "Требуется дополнительная проверка распределения обязанностей: количество обязанностей сторон может быть неравномерным."
  },
  "needs_specialist": [
    {
      "item": "Сложная формулировка ответственности/штрафов — требуется проверка специалистом.",
      "clause_ref": "п. —"
    }
  ],
  "missing_sections": ["форс-мажор"],
  "disclaimer": "Отчёт сформирован автоматически и не является юридической консультацией."
}"""

INSTRUCTIONS = (
    "Сформируй отчёт строго по структуре и типам, как в примере JSON.\n"
    "Правила заполнения:\n"
    "- summary: строго 5–7 пунктов.\n"
    "- clause_ref, если неизвестно: ставь \"—\".\n"
    "- risk_map/atypical/contradictions/needs_specialist/missing_sections могут быть пустыми, "
    "но старайся найти хотя бы 2–4 элемента в risk_map, если в тексте есть материал.\n"
    "- duties_balance: заполни численно (примерно), если нельзя — поставь 0 и нейтральную note.\n"
    "- overall_status выбирай из: "
    "\"Низкий уровень внимания\" / \"Средний уровень внимания\" / \"Повышенное внимание\".\n"
    "- missing_sections выбирай из: \"форс-мажор\" / \"ответственность\" / \"порядок расторжения\".\n"
)

def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан")
    return OpenAI(api_key=api_key)

def _build_user_message(contract_type: str, text: str, pages: int) -> str:
    return (
        f"Тип договора: {contract_type}\n"
        f"Страниц (по файлу): {pages}\n\n"
        "Ниже пример СТРОГОЙ структуры JSON (ориентир по полям и типам):\n"
        f"{JSON_TEMPLATE_EXAMPLE}\n\n"
        f"{INSTRUCTIONS}\n\n"
        "Текст договора (может быть обрезан):\n"
        f"{text}"
    )

def _validate_report(payload: str) -> Report:
    return Report.model_validate_json(payload)

def _post_fix(report: Report, contract_type: str, pages: int) -> Report:
    # Принудительно проставляем то, что точно знаем из файла/контекста
    try:
        report.cover.contract_type = contract_type
    except Exception:
        pass
    try:
        report.cover.pages = int(pages) if pages else 1
    except Exception:
        pass
    try:
        report.cover.analysis_date = date.today()
    except Exception:
        pass

    # summary строго 5–7 пунктов
    base_fill = [
        "Обратите внимание на сроки и порядок исполнения обязательств.",
        "Обратите внимание на порядок приёмки результата и подтверждающие документы.",
        "Проверьте условия оплаты: сроки, этапность, основания для удержаний/штрафов.",
        "Проверьте ответственность сторон и возможные ограничения ответственности.",
        "Обратите внимание на порядок расторжения и сроки уведомления.",
        "Проверьте раздел конфиденциальности и условия передачи информации третьим лицам.",
        "Проверьте порядок разрешения споров и применимое право (если указано).",
    ]
    try:
        summary = list(report.summary) if getattr(report, "summary", None) else []
        summary = [s for s in summary if isinstance(s, str) and s.strip()]
        while len(summary) < 5:
            summary.append(base_fill[len(summary) % len(base_fill)])
        if len(summary) > 7:
            summary = summary[:7]
        report.summary = summary  # type: ignore[attr-defined]
    except Exception:
        pass

    return report

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
        report = _validate_report(content)
        return _post_fix(report, contract_type, pages)
    except ValidationError:
        retry_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Исправь JSON: он должен быть строго по структуре примера. "
                        "Верни только валидный JSON без лишних полей.\n\n" + content
                    ),
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        retry_content = retry_response.choices[0].message.content or ""
        report = _validate_report(retry_content)
        return _post_fix(report, contract_type, pages)

