import os
import base64
from postmarker.core import PostmarkClient
from dotenv import load_dotenv
from jinja2 import Template

load_dotenv()

POSTMARK_API_TOKEN = os.getenv("POSTMARK_API_TOKEN")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
TEMPLATE_DIR = "templates"

def send_email(
    recipient_email: str,
    subject: str,
    html_template: str,
    context: dict,
    attachments: list[str] = None,
):
    """
    Generic email sender using Postmark + HTML templates.

    Args:
        recipient_email: Email of recipient.
        subject: Email subject.
        html_template: HTML file inside /templates.
        context: Dict of placeholders for template.
        attachments: List of file paths (PDF, CSV, etc.)
    """
    if not POSTMARK_API_TOKEN:
        raise ValueError("POSTMARK_API_TOKEN missing in environment.")
    postmark = PostmarkClient(server_token=POSTMARK_API_TOKEN)

    # Load HTML template and render with Jinja2
    with open(os.path.join(TEMPLATE_DIR, html_template), "r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)
    body = template.render(**context)

    print(context["payment_url"])

    # Prepare attachments
    attachments_list = []
    if attachments:
        for file_path in attachments:
            if not os.path.exists(file_path):
                print(f"⚠️ Skipping missing attachment: {file_path}")
                continue
            mime_type = "application/pdf" if file_path.endswith(".pdf") else "text/csv"
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            attachments_list.append({
                "Name": os.path.basename(file_path),
                "Content": encoded,
                "ContentType": mime_type
            })

    # Send email via Postmark
    postmark.emails.send(
        From=SENDER_EMAIL,
        To=recipient_email,
        Subject=subject,
        HtmlBody=body,
        Attachments=attachments_list
    )
    print(f"✅ Email sent to {recipient_email} ({len(attachments_list)} attachment(s))")
