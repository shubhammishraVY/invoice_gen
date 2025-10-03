from datetime import datetime, timedelta, timezone
from repositories.calls_repo import get_calls_from_top_level, get_calls_from_company_doc
from repositories.companies_repo import get_company_billing_details
from repositories.invoice_repo import save_invoice,get_invoice
import math



def generate_monthly_bill(company: str = "vysedeck", month: int | None = None, year: int | None = None):
    """Generate structured monthly bill for a company."""

    now = datetime.now(timezone.utc)

    # Fallback → last completed month
    if month is None or year is None:
        last_month_date = (now.replace(day=1) - timedelta(days=1))
        month = month or last_month_date.month
        year = year or last_month_date.year

    # Billing cycle start & end
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)


    # billing_service.py
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
    active_address = None
    for addr in billingInfo.get("billingAddresses", []):
        if addr.get("isActive"):
            active_address = addr
            break

    company_info = {
        "legalName": billingInfo.get("legalName"),
        "billingEmail": billingInfo.get("billingEmail"),
        "bankName": billingInfo.get("bankName"),
        "accountNumber": billingInfo.get("accountNumber"),
        "ifscCode": billingInfo.get("ifscCode"),
        "billingAddress": active_address,  # only active one
    }

    # --- Invoice metadata ---
    invoice_date = now
    due_date = now + timedelta(days=7)

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
