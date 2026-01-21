from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


class PdfRenderer:
    def __init__(self, templates_path: Path, static_path: Path) -> None:
        self.templates_path = templates_path
        self.static_path = static_path
        self.env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, context: dict[str, Any]) -> bytes:
        template = self.env.get_template(template_name)
        html = template.render(**context, for_pdf=True)
        return HTML(string=html, base_url=str(self.static_path)).write_pdf()
