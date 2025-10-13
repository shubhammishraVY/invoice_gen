# services/pdf_service.py
import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../invoices")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_pdf(template_name: str, data: dict, prefix: str = "document") -> str:
    """
    Generic PDF generator using Jinja2 and WeasyPrint.

    Args:
        template_name: HTML template file in /templates.
        data: Dictionary of template variables.
        prefix: 'invoice', 'receipt', etc.

    Returns:
        str: Path to generated PDF file.
    """
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(template_name)
        html_content = template.render(**data)

        # Generate safe filename
        doc_id = data.get("invoice_number") or data.get("receipt_number") or datetime.now().isoformat()
        safe_name = doc_id.replace(":", "-").replace("/", "-")
        file_name = f"{prefix}_{safe_name}.pdf"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        HTML(string=html_content).write_pdf(file_path)
        print(f"✅ PDF generated: {file_path}")
        return file_path
    except Exception as e:
        raise RuntimeError(f"Failed to generate {prefix} PDF: {e}")
