import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../invoices")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_invoice_pdf(invoice_data: dict) -> str:
    """Generate PDF invoice from template and return file path."""
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("invoice_template.html")

        html_content = template.render(**invoice_data)
        
        # --- FIX: Sanitize Filename ---
        # The invoice_number is a timestamp string (e.g., '2025-09-01T00:00:00+00:00_...').
        # The colon (:) character is illegal in Windows file paths, causing [Errno 22].
        file_name_raw = invoice_data['invoice_number']
        safe_file_name = file_name_raw.replace(':', '-') # Replace illegal colons with hyphens
        
        file_name = f"{safe_file_name}.pdf" 
        file_path = os.path.join(OUTPUT_DIR, file_name)

        HTML(string=html_content).write_pdf(file_path)

        return file_path
    except Exception as e:
        # Provide a clearer error message for the specific Invalid argument error
        if "[Errno 22]" in str(e):
             raise RuntimeError(f"Failed to generate PDF due to invalid filename characters. Please check the invoice ID structure. Original error: {str(e)}")
        raise RuntimeError(f"Failed to generate PDF: {str(e)}")
