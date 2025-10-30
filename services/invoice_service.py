# services/invoice_service.py
from repositories.companies_repo import get_tenants
from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from datetime import datetime, timedelta
from utils.date_utils import localize_datetime_fields
from utils.invoice_token import generate_invoice_token
import os

FRONTEND_PAYMENT_URL = os.getenv("FRONTEND_PAYMENT_URL", "https://billai.vysedeck.com/pay")

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
        payment_url = "https://billai.vysedeck.com/login"

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


def check_and_send_payment_reminders():
    """
    Checks all pending invoices and sends reminder emails based on:
    1. First reminder: 3 days after invoice_date
    2. Final reminder: On due_date
    
    This function should be called daily by the scheduler.
    """
    try:
        print(f"\n🔔 [{datetime.now()}] Checking for payment reminders...")
        
        from repositories.bill_repo import get_all_pending_invoices
        
        pending_invoices = get_all_pending_invoices()
        
        if not pending_invoices:
            print("✅ No pending invoices found")
            return {"first_reminders_sent": 0, "final_reminders_sent": 0}
        
        today = datetime.now().date()
        first_reminders_sent = 0
        final_reminders_sent = 0
        
        for invoice_entry in pending_invoices:
            invoice_data = invoice_entry["invoice_data"]
            company_id = invoice_entry["company_id"]
            tenant_id = invoice_entry["tenant_id"]
            
            try:
                # Parse dates
                invoice_date_str = invoice_data.get("invoiceDate", "")
                due_date_str = invoice_data.get("dueDate", "")
                
                if not invoice_date_str or not due_date_str:
                    print(f"⚠️ Skipping invoice {invoice_data.get('invoice_number')}: Missing dates")
                    continue
                
                # Extract date part (YYYY-MM-DD)
                invoice_date = datetime.strptime(invoice_date_str[:10], "%Y-%m-%d").date()
                due_date = datetime.strptime(due_date_str[:10], "%Y-%m-%d").date()
                
                # Calculate reminder dates
                first_reminder_date = invoice_date + timedelta(days=3)
                
                # Check if we need to send reminders
                if today == first_reminder_date:
                    # Send first reminder
                    print(f"📧 Sending first reminder for invoice {invoice_data.get('invoice_number')}")
                    _send_reminder_email(invoice_data, company_id, tenant_id, reminder_type="first")
                    first_reminders_sent += 1
                    
                elif today == due_date:
                    # Send final reminder
                    print(f"📧 Sending final reminder for invoice {invoice_data.get('invoice_number')}")
                    _send_reminder_email(invoice_data, company_id, tenant_id, reminder_type="final")
                    final_reminders_sent += 1
                    
            except Exception as e:
                print(f"❌ Error processing reminder for invoice {invoice_data.get('invoice_number')}: {e}")
        
        summary = {
            "first_reminders_sent": first_reminders_sent,
            "final_reminders_sent": final_reminders_sent,
            "message": f"Sent {first_reminders_sent} first reminders and {final_reminders_sent} final reminders"
        }
        print(f"✅ {summary['message']}")
        return summary
        
    except Exception as e:
        print(f"❌ Failed to check payment reminders: {e}")
        raise


def _send_reminder_email(invoice_data: dict, company_id: str, tenant_id: str | None, reminder_type: str):
    """
    Helper function to send reminder emails with invoice PDF attached.
    
    Args:
        invoice_data: Invoice data dictionary
        company_id: Company ID
        tenant_id: Tenant ID (or None)
        reminder_type: "first" or "final"
    """
    try:
        # Convert to company timezone for email readability
        tzone = invoice_data.get("tzone")
        invoice_data = localize_datetime_fields(invoice_data, tzone)
        
        # Generate Currency Symbol
        currency = invoice_data.get("billingRates", {}).get("currency", "INR").upper()
        symbol_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "SGD": "S$", "JPY": "¥"}
        currency_symbol = symbol_map.get(currency, currency)
        invoice_data["currency_symbol"] = currency_symbol
        
        # Generate PDF
        pdf_path = generate_pdf("invoice_template.html", invoice_data, prefix="invoice")
        
        # Prepare email context
        company_info = invoice_data.get("companyInfo", {})
        vendor_info = invoice_data.get("vendorInfo", {})
        billing_period = invoice_data.get("billingPeriod", {})
        
        recipient_email = "vishruth.ramesh@vysedeck.com"  # Same as in send_invoice_to_client
        sender_email = vendor_info.get("billingEmail", "")
        invoice_number = invoice_data.get("invoice_number")
        
        start_date = billing_period.get("startDate", "")[:10]
        end_date = billing_period.get("endDate", "")[:10]
        
        # Payment URL
        payment_url = "https://billai.vysedeck.com/login"
        
        # Select template and subject based on reminder type
        if reminder_type == "first":
            template = "reminder_email_template.html"
            subject = f"Payment Reminder - Invoice {invoice_number}"
        else:  # final
            template = "final_reminder_email_template.html"
            subject = f"URGENT: Final Payment Reminder - Invoice {invoice_number} Due Today"
        
        context = {
            "legalName": vendor_info.get("legalName"),
            "invoice_number": invoice_number,
            "start_date": start_date,
            "end_date": end_date,
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
            "invoice_date": invoice_data.get('invoiceDate', '')[:10],
            "sender_email": sender_email,
            "payment_url": payment_url,
            "reminder_type": reminder_type
        }
        
        # Send email with PDF attachment
        send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_template=template,
            context=context,
            attachments=[pdf_path]
        )
        
        print(f"✅ {reminder_type.capitalize()} reminder sent for invoice {invoice_number}")
        
    except Exception as e:
        print(f"❌ Failed to send {reminder_type} reminder email: {e}")
        raise