import os
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.base import MIMEBase
# from email.mime.text import MIMEText
# from email import encoders
from postmarker.core import PostmarkClient
import base64   
from dotenv import load_dotenv

load_dotenv()

# # --- Configuration ---
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT"))
POSTMARK_API_TOKEN = os.getenv("POSTMARK_API_TOKEN")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
# SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
TEMPLATE_PATH = "templates/invoice_email_template.html"
# ----------------------

def send_invoice_email(recipient_email: str, company_name: str, invoice_number: str, pdf_path: str, csv_path: str, invoice_data: dict):
    """
    Sends an invoice email with the PDF invoice and CSV call log attached.

    Args:
        recipient_email: The client's billing email address.
        company_name: The client's legal company name.
        invoice_number: The unique invoice identifier.
        pdf_path: Local file path to the generated PDF invoice.
        csv_path: Local file path to the generated CSV call log.
        invoice_data: Dictionary containing all billing details for the email body.
    """
    if not POSTMARK_API_TOKEN:
        raise ValueError("POSTMARK_API_TOKEN environment variable is not set.")
    postmark = PostmarkClient(server_token=POSTMARK_API_TOKEN)
    try:
        # --- Extract billing details for email body ---
        usage_data = invoice_data.get('usageData', {})
        total_calls = usage_data.get('totalCalls', 0)
        total_billed_minutes = usage_data.get('totalBilledMinutes', 0)

        billing_rates = invoice_data.get('billingRates', {})
        rate_per_minute = billing_rates.get('ratePerMinute', 0)
        maintenance_fee = billing_rates.get('maintenanceFee', 0)
        gst_rate = billing_rates.get('gstRate', 0)
        currency = invoice_data.get('billingRates.currency', 'INR')

        subtotal = invoice_data.get('subtotal', 0)
        gst_amount = invoice_data.get('gstAmount', 0)
        total_amount = invoice_data.get('totalAmount', 0)

        billing_period = invoice_data.get('billingPeriod', {})
        # Slicing dates to ensure only the date part is used
        start_date = billing_period.get('startDate', '')[:10]
        end_date = billing_period.get('endDate', '')[:10]
        due_date = invoice_data.get('dueDate', '')[:10]

        call_charges = subtotal - maintenance_fee
        currency_symbol = "₹" if currency == "INR" else currency

        # --- Load and fill HTML template ---
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_str = f.read()
        
        # Use string formatting to insert variables into the HTML template
        body = template_str.format(
            invoice_number=invoice_number,
            start_date=start_date,
            end_date=end_date,
            total_calls=f"{total_calls:,}",
            total_billed_minutes=f"{total_billed_minutes:,}",
            rate_per_minute=f"{rate_per_minute:.2f}",
            call_charges=f"{call_charges:,.2f}",
            maintenance_fee=f"{maintenance_fee:,.2f}",
            subtotal=f"{subtotal:,.2f}",
            gst_rate=gst_rate,
            gst_amount=f"{gst_amount:,.2f}",
            total_amount=f"{total_amount:,.2f}",
            currency_symbol=currency_symbol,
            due_date=due_date,
            sender_email=SENDER_EMAIL,
        )

        attachments_list = []

        def encode_attachment(file_path: str, mime_type: str):
            with open(file_path, "rb") as f:
                encoded_content = base64.b64encode(f.read()).decode('utf-8')
            return{
                "Name": os.path.basename(file_path),
                "Content": encoded_content,
                "ContentType": mime_type
            }
        
        # 1. Attach PDF
        attachments_list.append(encode_attachment(
            pdf_path,
            "application/pdf"
        ))

        # 2. Attach CSV
        if csv_path and os.path.exists(csv_path):
            attachments_list.append(encode_attachment(
                csv_path,
                "text/csv"
            ))
            print(f"Prepared CSV file for API: {os.path.basename(csv_path)}")
        elif csv_path:
            print(f"Warning: CSV file not found at path: {csv_path}. Skipping attachment.")


        # --- Send email via Postmark API ---
        postmark.emails.send(
            From=SENDER_EMAIL,
            To=recipient_email,
            Subject=f"Tax Invoice {invoice_number} - Voice Agent Services for {start_date} to {end_date}",
            HtmlBody=body,
            Attachments=attachments_list
        )
        
        print(f"Invoice email sent successfully via Postmark API to {recipient_email}")

    except Exception as e:
        print(f"Error sending invoice email: {e}")
        # Re-raise the exception to be caught by the calling function (invoice_service)
        raise
