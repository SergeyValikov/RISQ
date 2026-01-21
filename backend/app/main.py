from __future__ import annotations

import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from backend.app.schemas.report import Report
from backend.app.services.analyzer_llm import analyze_contract
from backend.app.services.parser import parse_document
from backend.app.services.pdf_render import PdfRenderer
from backend.app.services.storage import InMemoryStorage

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
storage = InMemoryStorage()
pdf_renderer = PdfRenderer(TEMPLATES_DIR, STATIC_DIR)

CONTRACT_TYPES = ["Договор оказания услуг"]


def _render_report_context(report: Report) -> dict:
    """
    Контекст для HTML / PDF отчёта
    """
    return {
        "report": report,
        "analysis_date": report.cover.analysis_date,
        "text_chars": getattr(report.cover, "chars", None),
        "text_words": getattr(report.cover, "words", None),
    }


def _run_analysis(job_id: str, contract_type: str, file_path: Path) -> None:
    """
    Фоновая задача анализа договора
    """
    try:
        storage.set_status(job_id, "processing", "Извлечение текста…")

        # 1. Парсим документ
        text, pages = parse_document(file_path)

        # 2. Считаем объём текста
        text_chars = len(text)
        text_words = len(text.split())

        # 3. Анализ
        storage.set_status(job_id, "processing", "Анализ структуры…")
        report = analyze_contract(contract_type, text, pages)

        # 4. Прокидываем объём текста в отчёт
        try:
            report.cover.chars = text_chars
            report.cover.words = text_words
        except Exception:
            pass

        # 5. Сохраняем результат
        storage.set_status(job_id, "processing", "Формирование отчёта…")
        storage.set_report(job_id, report)

    except Exception as exc:
        storage.set_status(job_id, "error", "Ошибка анализа", str(exc))

    finally:
        if file_path.exists():
            file_path.unlink(missing_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload(request: Request) -> Response:
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "contract_types": CONTRACT_TYPES,
        },
    )


@app.post("/analyze")
async def analyze(
    background_tasks: BackgroundTasks,
    contract_type: str = Form(...),
    file: UploadFile = File(...),
) -> Response:
    if contract_type not in CONTRACT_TYPES:
        raise HTTPException(status_code=400, detail="Неизвестный тип договора")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")

    suffix = Path(file.filename).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        temp_path = Path(tmp.name)

    job = storage.create_job()
    background_tasks.add_task(_run_analysis, job.job_id, contract_type, temp_path)

    return RedirectResponse(url=f"/analyzing/{job.job_id}", status_code=303)


@app.get("/analyzing/{job_id}", response_class=HTMLResponse)
async def analyzing(request: Request, job_id: str) -> Response:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return templates.TemplateResponse(
        "analyzing.html",
        {"request": request, "job_id": job_id},
    )


@app.get("/report/{job_id}", response_class=HTMLResponse)
async def report(request: Request, job_id: str) -> Response:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if job.status != "done" or not job.report:
        raise HTTPException(status_code=409, detail="Отчёт ещё не готов")

    context = _render_report_context(job.report)
    context.update({"request": request, "job_id": job_id})

    return templates.TemplateResponse("report.html", context)


@app.get("/report/{job_id}/pdf")
async def report_pdf(job_id: str) -> Response:
    job = storage.get_job(job_id)
    if not job or job.status != "done" or not job.report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    context = _render_report_context(job.report)
    pdf_bytes = pdf_renderer.render("report.html", context)

    headers = {
        "Content-Disposition": f"attachment; filename=risq-report-{job_id}.pdf"
    }
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )


@app.get("/api/job/{job_id}")
async def api_job(job_id: str) -> JSONResponse:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    payload = {
        "status": job.status,
        "step": job.step,
    }
    if job.error:
        payload["error"] = job.error

    return JSONResponse(payload)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True})

