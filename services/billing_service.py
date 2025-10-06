from datetime import datetime, timedelta, timezone
from repositories.callLogs_repo import get_calls_from_top_level, get_calls_from_company_doc
from repositories.companies_repo import get_company_billing_details
from repositories.bill_repo import save_invoice, get_invoice
import math
from repositories.companies_repo import get_all_companies

# Use the current time for reference
NOW = datetime.now(timezone.utc)


def convert_number_to_words(num: float) -> str:
    """
    Convert number to Indian numbering system words.
    Returns format: "Rupees One Thousand Five Hundred Only"
    """
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 
             'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    def convert_hundreds(n: int) -> str:
        result = ''
        if n >= 100:
            result += ones[n // 100] + ' Hundred '
            n %= 100
        if n >= 20:
            result += tens[n // 10] + ' '
            n %= 10
        elif n >= 10:
            result += teens[n - 10] + ' '
            return result.strip()
        if n > 0:
            result += ones[n] + ' '
        return result.strip()
    
    if num == 0:
        return 'Zero Rupees Only'
    
    # Split into integer and decimal parts
    integer_part = int(num)
    decimal_part = round((num - integer_part) * 100)
    
    result = ''
    
    # Crores
    crores = integer_part // 10000000
    if crores > 0:
        result += convert_hundreds(crores) + ' Crore '
        integer_part %= 10000000
    
    # Lakhs
    lakhs = integer_part // 100000
    if lakhs > 0:
        result += convert_hundreds(lakhs) + ' Lakh '
        integer_part %= 100000
    
    # Thousands
    thousands = integer_part // 1000
    if thousands > 0:
        result += convert_hundreds(thousands) + ' Thousand '
        integer_part %= 1000
    
    # Remaining hundreds
    if integer_part > 0:
        result += convert_hundreds(integer_part) + ' '
    
    result = 'Rupees ' + result.strip()
    
    # Add paise if present
    if decimal_part > 0:
        result += ' and ' + convert_hundreds(decimal_part) + ' Paise'
    
    result += ' Only'
    
    return result


def determine_place_of_supply(address: dict) -> str:
    """
    Determine place of supply from GST number.
    First 2 digits of GSTIN indicate state code.
    """
    gst_number = address.get("gstNumber", "") if address else ""
    state_code = gst_number[:2] if gst_number and len(gst_number) >= 2 else "09"
    
    # Indian state GST codes
    state_map = {
        "01": "Jammu and Kashmir (01)",
        "02": "Himachal Pradesh (02)",
        "03": "Punjab (03)",
        "04": "Chandigarh (04)",
        "05": "Uttarakhand (05)",
        "06": "Haryana (06)",
        "07": "Delhi (07)",
        "08": "Rajasthan (08)",
        "09": "Uttar Pradesh (09)",
        "10": "Bihar (10)",
        "11": "Sikkim (11)",
        "12": "Arunachal Pradesh (12)",
        "13": "Nagaland (13)",
        "14": "Manipur (14)",
        "15": "Mizoram (15)",
        "16": "Tripura (16)",
        "17": "Meghalaya (17)",
        "18": "Assam (18)",
        "19": "West Bengal (19)",
        "20": "Jharkhand (20)",
        "21": "Odisha (21)",
        "22": "Chhattisgarh (22)",
        "23": "Madhya Pradesh (23)",
        "24": "Gujarat (24)",
        "27": "Maharashtra (27)",
        "29": "Karnataka (29)",
        "30": "Goa (30)",
        "32": "Kerala (32)",
        "33": "Tamil Nadu (33)",
        "34": "Puducherry (34)",
        "35": "Andaman and Nicobar Islands (35)",
        "36": "Telangana (36)",
        "37": "Andhra Pradesh (37)",
    }
    
    return state_map.get(state_code, "Uttar Pradesh (09)")


# def generate_monthly_bill_for_all():
#     """Generate invoices for all companies for the previous month."""
#     now = datetime.now(timezone.utc)
#     last_month_date = (now.replace(day=1) - timedelta(days=1))

#     month = last_month_date.month
#     year = last_month_date.year

#     companies = get_all_companies()
#     invoices = []

#     for company_id in companies:
#         try:
#             invoice = generate_monthly_bill(company_id, month, year)
#             invoices.append(invoice)
#         except Exception as e:
#             print(f"Failed to generate invoice for {company_id}: {e}")

#     return invoices


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
        # FIX: Ensure existing invoice also has the invoice_number field for pdf_service
        existing_invoice["invoice_number"] = existing_invoice["id"] 
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

    # --- Build line items array for detailed invoice breakdown ---
    line_items = [
        {
            "description": f"Call Charges - {total_minutes} min × ₹{ratePerMin}/min",
            "quantity": total_minutes,
            "rate": ratePerMin,
            "amount": round(rawAmt, 2)
        }
    ]
    
    # Add maintenance fee if applicable
    if maintenanceFee > 0:
        line_items.append({
            "description": "Monthly Platform Maintenance Fee",
            "quantity": 1,
            "rate": maintenanceFee,
            "amount": maintenanceFee
        })

    # --- Apply rounding to nearest integer ---
    initial_total = subtotal + gstAmount
    final_total = round(initial_total)
    round_off = final_total - initial_total
    apply_rounding = abs(round_off) > 0.01

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

    # --- Extract additional billing fields ---
    currency = billing.get("currency", "INR")
    purchase_order = billing.get("purchaseOrder", "N/A")
    po_date = billing.get("poDate")
    
    # --- Calculate place of supply and total in words ---
    place_of_supply = determine_place_of_supply(active_address)
    total_in_words = convert_number_to_words(final_total)

    invoice_data = {
        "usageData": {
            "billingPolicy": billing.get("billingPolicy"),
            "totalBilledMinutes": total_minutes,
            "totalCalls": total_calls_top + total_calls_nested,
            "totalSeconds": total_seconds,
        },
        "lineItems": line_items,
        "subtotal": round(subtotal, 2),
        "gstAmount": round(gstAmount, 2),
        "roundOff": round(round_off, 2) if apply_rounding else 0,
        "totalAmount": round(final_total, 2),
        "totalInWords": total_in_words,
        "currency": currency,
        "placeOfSupply": place_of_supply,
        "purchaseOrder": purchase_order,
        "poDate": po_date.isoformat() if po_date else None,
        "invoiceDate": invoice_date.isoformat(),
        "dueDate": due_date.isoformat(),
        "companyInfo": company_info,
        "companyId": company,
        "billingRates": billing,
        "billingPeriod": {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat()
        },
        "authorizedSignatory": {
            "name": "Shashank Trivedi",
            "designation": "Director",
            "company": "VYSEDECK AI Ventures Pvt Ltd"
        }
    }

    # 🔹 Save invoice in Firestore
    saved_invoice = save_invoice(company, invoice_data)

    print("the saved invoice details are: ",saved_invoice.get("id"))
    
    # CRITICAL: Add the unique doc ID to the data, which pdf_service uses for file naming.
    invoice_data["invoice_number"] = saved_invoice.get("id")

    return invoice_data