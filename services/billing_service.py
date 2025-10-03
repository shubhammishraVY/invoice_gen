from datetime import datetime, timedelta, timezone
from repositories.calls_repo import get_calls_from_top_level, get_calls_from_company_doc
from repositories.companies_repo import get_company_billing_details
from repositories.invoice_repo import save_invoice,get_invoice
import math
from repositories.companies_repo import get_all_companies

# Use the current time for reference
NOW = datetime.now(timezone.utc)





def generate_monthly_invoices_for_all():
    """Generate invoices for all companies for the previous month."""
    now = datetime.now(timezone.utc)
    last_month_date = (now.replace(day=1) - timedelta(days=1))

    month = last_month_date.month
    year = last_month_date.year

    companies = get_all_companies()
    invoices = []

    for company_id in companies:
        try:
            invoice = generate_monthly_bill(company_id, month, year)
            invoices.append(invoice)
        except Exception as e:
            print(f"Failed to generate invoice for {company_id}: {e}")

    return invoices





def generate_monthly_bill(company: str = "vysedeck", month: int | None = None, year: int | None = None):
    """
    Generate structured monthly bill for a company. 
    Handles fallbacks to the last completed month and checks for future dates.
    """

    # --- 1. Determine Target Month (with Fallback) ---
    target_month = month
    target_year = year

    if target_month is None or target_year is None:
        # Fallback to the last completed month
        last_month_date = (NOW.replace(day=1) - timedelta(days=1))
        target_month = target_month or last_month_date.month
        target_year = target_year or last_month_date.year

    month, year = target_month, target_year

    # --- 2. Future Date Check ---
    # Cannot generate a bill for the current month or any month in the future.
    # This prevents billing for uncompleted periods (e.g., trying to bill Oct on Oct 3rd).
    
    current_month_start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    requested_month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    
    if requested_month_start >= current_month_start:
         raise ValueError(
             f"Cannot generate bill for the current month ({NOW.month}/{NOW.year}) "
             "or a future period. The requested period must be fully completed."
         )

    # --- 3. Billing cycle start & end calculation (Robustly handles month lengths and year changes) ---
    start_date = requested_month_start
    
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    
    end_date = datetime(next_year, next_month, 1, tzinfo=timezone.utc) - timedelta(seconds=1)

    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()

    # 🔹 Check if invoice already exists
    existing_invoice = get_invoice(company, start_date_str, end_date_str)
    if existing_invoice:
        print("Returning existing invoice:", existing_invoice["id"])
        return existing_invoice
    
    
    # 🔹 Else generating invoice

    # Fetch company billing details
    billing_details = get_company_billing_details(company)
    if not billing_details:
        raise ValueError(f"No billing details found for company {company}")

    billing = billing_details.get("billing", {})
    billingInfo = billing_details.get("billingInfo", {})

    # Shorthand usage
    ratePerMin = billing_details.get("ratePerMinute") or 0
    gstRate = billing_details.get("gstRate") or 0
    maintenanceFee = billing_details.get("maintenanceFee") or 0

    # Fetch calls from both sources
    calls_top = get_calls_from_top_level(company, start_date, end_date)
    calls_nested = get_calls_from_company_doc(company, start_date, end_date)

    total_duration_top = sum(c.get("duration", 0) for c in calls_top)
    total_duration_nested = sum(c.get("duration", 0) for c in calls_nested)

    total_calls_top = len(calls_top)
    total_calls_nested = len(calls_nested)

    total_seconds = total_duration_top + total_duration_nested
    total_minutes = math.ceil(total_seconds / 60)

    # --- Billing calculation ---
    rawAmt = total_minutes * ratePerMin
    subtotal = rawAmt + maintenanceFee
    gstAmount = subtotal * (gstRate / 100)
    totalAmount = subtotal + gstAmount

    # --- Company Info (use active address only) ---
    active_address = next((addr for addr in billingInfo.get("billingAddresses", []) if addr.get("isActive")), None)

    company_info = {
        "legalName": billingInfo.get("legalName"),
        "billingEmail": billingInfo.get("billingEmail"),
        "bankName": billingInfo.get("bankName"),
        "accountNumber": billingInfo.get("accountNumber"),
        "ifscCode": billingInfo.get("ifscCode"),
        "billingAddress": active_address,  # only active one
    }

    # --- Invoice metadata ---
    invoice_date = NOW # Use the current time for the invoice generation date
    due_date = invoice_date + timedelta(days=7)

    invoice_data = {
        "usageData": {
            "billingPolicy": billing.get("billingPolicy"),
            "totalBilledMinutes": total_minutes,
            "totalCalls": total_calls_top + total_calls_nested,
            "totalSeconds": total_seconds,
        },
        "subtotal": round(subtotal, 2),
        "gstAmount": round(gstAmount, 2),
        "totalAmount": round(totalAmount, 2),
        "invoiceDate": invoice_date.isoformat(),
        "dueDate": due_date.isoformat(),
        "companyInfo": company_info,
        "companyId": company,
        "billingRates": billing,
        "billingPeriod": {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat()
        }
    }

    # 🔹 Save invoice in Firestore
    saved_invoice = save_invoice(company, invoice_data)

    print("the saved invoice details are: ",saved_invoice.get("id"))

    return invoice_data
