# services/invoice_service.py
from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from datetime import datetime
from utils.date_utils import localize_datetime_fields
import os

FRONTEND_PAYMENT_URL = os.getenv("FRONTEND_PAYMENT_URL", "https://portal.vysedeck.com/pay")

def _construct_csv_filepath(company_id: str, start_date_str: str, end_date_str: str) -> str:
    """Helper to construct the expected path of the generated CSV file."""
    try:
        start_date_formatted = datetime.strptime(start_date_str[:10], '%Y-%m-%d').strftime("%Y-%m-%d")
        end_date_formatted = datetime.strptime(end_date_str[:10], '%Y-%m-%d').strftime("%Y-%m-%d")
        filename = f"{company_id}_call_logs_{start_date_formatted}_to_{end_date_formatted}.csv"
        return f"invoices/{filename}"
    except Exception as e:
        print(f"Error constructing CSV path for {company_id}: {e}")
        return ""

def generate_invoices_for_all(companies: list[str], month: int, year: int):
    """Generate invoices for all companies, attach CSV + PDF, and email them."""
    generated_pdfs = []

    for company in companies:
        try:
            invoice_data = generate_monthly_bill(company, month, year)
            billing_period = invoice_data.get('billingPeriod', {})
            start_date = billing_period.get('startDate')
            end_date = billing_period.get('endDate')

            print("Timezone for company:", invoice_data.get('tzone'))
            invoice_data = localize_datetime_fields(invoice_data, invoice_data.get('tzone'))

            # --- PDF Generation (Generic) ---
            pdf_path = generate_pdf("invoice_template.html", invoice_data, prefix="invoice")

            # --- CSV Path Construction ---
            csv_path = None
            if start_date and end_date:
                csv_path = _construct_csv_filepath(company, start_date, end_date)

            # --- Email Preparation ---
            company_info = invoice_data.get('companyInfo', {})
            recipient_email = "vishruth.ramesh@vysedeck.com"
            company_name = company_info.get('legalName', company)
            invoice_number = invoice_data.get('invoice_number')

            # --- Currency Detection ---
            currency = invoice_data.get("billingRates", {}).get("currency", "INR").upper()
            currency_symbol_map = {
                "INR": "₹",
                "USD": "$",
                "EUR": "€",
                "GBP": "£",
                "SGD": "S$",
                "JPY": "¥"
            }
            currency_symbol = currency_symbol_map.get(currency, currency)


            if recipient_email and company_name and invoice_number:
                subject = f"Tax Invoice {invoice_number} - Voice Agent Services for {start_date[:10]} to {end_date[:10]}"

                # Prepare context for email template
                context = {
                    "invoice_number": invoice_number,
                    "start_date": start_date[:10],
                    "end_date": end_date[:10],
                    "total_calls": f"{invoice_data['usageData'].get('totalCalls', 0):,}",
                    "total_billed_minutes": f"{invoice_data['usageData'].get('totalBilledMinutes', 0):,}",
                    "rate_per_minute": f"{invoice_data['billingRates'].get('ratePerMinute', 0):.2f}",
                    "call_charges": f"{invoice_data['subtotal'] - invoice_data['billingRates'].get('maintenanceFee', 0):,.2f}",
                    "maintenance_fee": f"{invoice_data['billingRates'].get('maintenanceFee', 0):,.2f}",
                    "subtotal": f"{invoice_data['subtotal']:,.2f}",
                    "gst_rate": invoice_data['billingRates'].get('gstRate', 0),
                    "gst_amount": f"{invoice_data['gstAmount']:,.2f}",
                    "total_amount": f"{invoice_data['totalAmount']:,.2f}",
                    "currency_symbol": currency_symbol,
                    "due_date": invoice_data.get('dueDate', '')[:10],
                    "sender_email": os.getenv("SENDER_EMAIL"),
                    "payment_url": f"{FRONTEND_PAYMENT_URL}?invoice_id={invoice_number}"
                }

                # --- Send email (Generic Mailer) ---
                attachments = [pdf_path]
                if csv_path and os.path.exists(csv_path):
                    attachments.append(csv_path)

                send_email(
                    recipient_email=recipient_email,
                    subject=subject,
                    html_template="invoice_email_template.html",
                    context=context,
                    attachments=attachments
                )

                print(f"✅ Invoice and Call Log CSV mailed for {company} (ID: {invoice_number}): {pdf_path}")
            else:
                print(f"⚠️ Missing data for email: {company}")

            generated_pdfs.append({"company": company, "pdf": pdf_path, "csv": csv_path})

        except Exception as e:
            print(f"❌ Failed to process or mail invoice for {company}: {e}")

    return generated_pdfs
