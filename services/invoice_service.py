# services/invoice_service.py
from repositories.companies_repo import get_tenants
from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from datetime import datetime
from utils.date_utils import localize_datetime_fields
from utils.invoice_token import generate_invoice_token
import os

FRONTEND_PAYMENT_URL = os.getenv("FRONTEND_PAYMENT_URL", "https://portal.vysedeck.com/pay")

def _construct_csv_filepath(company_id: str, start_date_str: str, end_date_str: str) -> str:
    """Helper to construct expected CSV path."""
    try:
        start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        end_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        filename = f"{company_id}call_logs{start_date}to{end_date}.csv"
        return f"invoices/{filename}"
    except Exception as e:
        print(f"⚠ Error constructing CSV path for {company_id}: {e}")
        return ""

def send_invoice_to_client(invoice_data: dict, isSubEntity: bool):
    """Generates PDF, attaches CSV (if exists), and sends invoice email."""

    try:
        billing_period = invoice_data.get("billingPeriod", {})
        start_date = billing_period.get("startDate")
        end_date = billing_period.get("endDate")

        # Convert to company timezone for email readability
        tzone = invoice_data.get("tzone")
        invoice_data = localize_datetime_fields(invoice_data, tzone)

        #Generate Currency Symbol and adding it to invoice data
        currency = invoice_data.get("billingRates", {}).get("currency", "INR").upper()
        symbol_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "SGD": "S$", "JPY": "¥"}
        currency_symbol = symbol_map.get(currency, currency)

        invoice_data["currency_symbol"] = currency_symbol

        # --- Generate PDF ---
        pdf_path = generate_pdf("invoice_template.html", invoice_data, prefix="invoice")

        # --- Construct CSV path ---
        csv_path = None
        if start_date and end_date:
            csv_path = _construct_csv_filepath(invoice_data["companyId"], start_date, end_date)

        # --- Prepare email context ---
        company_info = invoice_data.get("companyInfo", {})
        # recipient_email = company_info.get("billingEmail", "support@vysedeck.com")
        recipient_email = "vishruth.ramesh@vysedeck.com"
        # company_name = company_info.get("legalName", invoice_data["companyId"])
        invoice_number = invoice_data.get("invoice_number")

        vendor_info = invoice_data.get("vendorInfo", {})
        sender_email = vendor_info.get("billingEmail", {})


        subject = (
            f"Tax Invoice {invoice_number} - Voice Agent Services for "
            f"{start_date[:10]} to {end_date[:10]}"
        )
        if isSubEntity:
            token = generate_invoice_token( invoice_data["vendorInfo"].get("id"), invoice_data["companyId"], invoice_data["invoice_number"], expires_in_hours=72 )
        else:
            token = generate_invoice_token( invoice_data["companyId"], None, invoice_data["invoice_number"], expires_in_hours=72 )

        # NOTE: token generation is left in place but we use the hardcoded payment URL
        # per request (no token appended).
        # Using provided hardcoded URL now:
        payment_url = "http://portal.vysedeck.com:5173/login"

        context = {
            "legalName": vendor_info.get("legalName"),
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
            "sender_email": sender_email,
            "payment_url": payment_url
        }

        # --- Attachments ---
        attachments = [pdf_path]
        if csv_path and os.path.exists(csv_path):
            attachments.append(csv_path)

        # --- Send email ---
        send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_template="invoice_email_template.html",
            context=context,
            attachments=attachments
        )

        print(f"✅ Invoice {invoice_number} sent to {recipient_email}")
        return {"invoice_number": invoice_number, "email": recipient_email, "pdf": pdf_path}

    except Exception as e:
        print(f"❌ Failed to send invoice email: {e}")
        return None

def generate_invoices_for_all(companies: list[str], month: int, year: int):
    """Generate invoices for all companies & tenants, then email them."""
    parent_company = "vysedeck"
    all_invoices = []
    for company in companies:
        try:
            # 1️⃣ Generate company’s own invoice
            invoice_company = generate_monthly_bill(
                company=parent_company, tenant=company, isSubEntity=False, month=month, year=year
            )
            all_invoices.append(invoice_company)
            send_invoice_to_client(invoice_company, isSubEntity = False)

            # 2️⃣ Generate invoices for all tenants under this company
            tenants = get_tenants(company)
            print(f"🏢 Tenants under {company}: {tenants}")
            for tenant in tenants:
                invoice_tenant = generate_monthly_bill(
                    company=company, tenant=tenant, isSubEntity = True, month=month, year=year
                )
                all_invoices.append(invoice_tenant)
                send_invoice_to_client(invoice_tenant, isSubEntity = True)

        except Exception as e:
            print(f"❌ Failed for {company}: {e}")

    return all_invoices