# services/invoice_service_copy.py
# This file is used by the fastAPI route only
import os
from datetime import datetime
from typing import Dict, Any

from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from utils.date_utils import localize_datetime_fields
from utils.invoice_token import generate_invoice_token

FRONTEND_PAYMENT_URL = os.getenv("FRONTEND_PAYMENT_URL", "https://billai.vysedeck.com/login")


def _construct_csv_filepath(company_id: str, start_date_str: str, end_date_str: str) -> str:
    """Helper to construct the expected path of the generated CSV file."""
    try:
        # Format the dates correctly, ensuring only the date part is used
        start_date_formatted = datetime.strptime(start_date_str[:10], '%Y-%m-%d').strftime("%Y-%m-%d")
        end_date_formatted = datetime.strptime(end_date_str[:10], '%Y-%m-%d').strftime("%Y-%m-%d")
        filename = f"{company_id}_call_logs_{start_date_formatted}_to_{end_date_formatted}.csv"
        # Assuming all generated files go into the 'invoices' directory
        return f"invoices/{filename}"
    except Exception as e:
        print(f"⚠️ Error constructing CSV path for {company_id}: {e}")
        return ""


def generate_invoice_for_company(
    company_id: str,
    tenant_id: str,
    month: int | None = None,
    year: int | None = None
) -> Dict[str, Any] | None:
    """
    Generates an invoice for a company/tenant, creates PDF, attaches CSV, and emails it.
    
    Automatically determines if this is a sub-entity relationship:
    - If company_id == "vysedeck": Main entity (not a sub-entity)
    - If company_id != "vysedeck": Sub-entity relationship
    
    Args:
        company_id: The parent company ID (e.g., 'vysedeck')
        tenant_id: The tenant/client ID
        month: Month (1-12). Defaults to last completed month
        year: Year. Defaults to current year if not provided
    
    Returns:
        Dict[str, Any]: Invoice data on success, None on failure
    """
    
    # Determine if this is a sub-entity relationship based on company_id
    is_sub_entity = (company_id.lower() != "vysedeck")
    
    if is_sub_entity:
        print(f"📄 Generating SUB-ENTITY invoice: company={company_id}, tenant={tenant_id}")
    else:
        print(f"📄 Generating MAIN ENTITY invoice: company={company_id}, tenant={tenant_id}")
    
    try:
        # 1️⃣ Generate invoice data using billing service
        invoice_data = generate_monthly_bill(
            company=company_id,
            tenant=tenant_id,
            isSubEntity=is_sub_entity,
            month=month,
            year=year
        )
        
        # Check if the billing service returned data
        if not invoice_data:
            print(f"❌ Billing service returned no data for tenant {tenant_id}")
            return None

        # 2️⃣ Get billing period and timezone
        billing_period = invoice_data.get('billingPeriod', {})
        start_date = billing_period.get('startDate')
        end_date = billing_period.get('endDate')
        tzone = invoice_data.get('tzone', 'UTC')

        print(f"🌍 Timezone for the company is: {tzone}")

        # 3️⃣ Localize datetime fields to company timezone
        invoice_data = localize_datetime_fields(invoice_data, tzone)

        # 4️⃣ Generate currency symbol and add to invoice data
        currency = invoice_data.get("billingRates", {}).get("currency", "INR").upper()
        symbol_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "SGD": "S$", "JPY": "¥"}
        currency_symbol = symbol_map.get(currency, currency)
        invoice_data["currency_symbol"] = currency_symbol

        # 5️⃣ Generate PDF
        pdf_path = generate_pdf("invoice_template.html", invoice_data, prefix="invoice")
        print(f"📑 PDF generated at: {pdf_path}")
        
        # 6️⃣ Construct CSV path
        csv_path = None
        if start_date and end_date:
            csv_path = _construct_csv_filepath(tenant_id, start_date, end_date)
            if not os.path.exists(csv_path):
                print(f"⚠️ CSV file not found at {csv_path}")
                csv_path = None
        
        # 7️⃣ Prepare email context
        company_info = invoice_data.get('companyInfo', {})
        vendor_info = invoice_data.get('vendorInfo', {})
        invoice_number = invoice_data.get('invoice_number')
        
        # For production, use: recipient_email = company_info.get('billingEmail')
        # For testing:
        recipient_email = "vishruth.ramesh@vysedeck.com"
        
        sender_email = vendor_info.get("billingEmail", os.getenv("SENDER_EMAIL"))

        # 8️⃣ Generate payment token
        if is_sub_entity:
            token = generate_invoice_token(
                vendor_info.get("id"),
                company_id,
                invoice_number,
                expires_in_hours=72
            )
        else:
            token = generate_invoice_token(
                company_id,
                None,
                invoice_number,
                expires_in_hours=72
            )

        # Use hardcoded payment URL as per invoice_service.py
        payment_url = FRONTEND_PAYMENT_URL

        # 9️⃣ Build email subject
        subject = (
            f"Tax Invoice {invoice_number} - Voice Agent Services for "
            f"{start_date[:10]} to {end_date[:10]}"
        )

        # 🔟 Build email context
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

        # 1️⃣1️⃣ Prepare attachments
        attachments = [pdf_path]
        if csv_path and os.path.exists(csv_path):
            attachments.append(csv_path)
            print(f"📎 Adding CSV attachment: {csv_path}")

        # 1️⃣2️⃣ Send email
        if recipient_email and invoice_number:
            send_email(
                recipient_email=recipient_email,
                subject=subject,
                html_template="invoice_email_template.html",
                context=context,
                attachments=attachments
            )
            print(f"✅ Invoice {invoice_number} emailed to {recipient_email} with {len(attachments)} attachment(s)")
        else:
            missing_fields = []
            if not recipient_email: missing_fields.append('recipient_email')
            if not invoice_number: missing_fields.append('invoice_number')
            print(f"⚠️ Skipping email. Missing critical data: {', '.join(missing_fields)}")
            
        # Return the structured data
        return invoice_data
            
    except ValueError as ve:
        # Handle specific validation errors from billing service
        print(f"❌ Validation error for tenant {tenant_id}: {ve}")
        raise  # Re-raise to be handled by route
    except Exception as e:
        print(f"❌ Failed to process invoice for tenant {tenant_id}: {e}")
        return None