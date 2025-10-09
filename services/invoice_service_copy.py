#this file is used by the fastAPI route only
import os
from datetime import datetime
from typing import Dict, Any, List

from repositories.companies_repo import get_all_companies 

from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_invoice_pdf
from services.mailer_service import send_invoice_email 
from utils.date_utils import localize_datetime_fields



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
        print(f"Error constructing CSV path for {company_id}: {e}")
        return ""
    
def _get_company_name_if_exists(company_name: str) -> str | None:
    """
    Checks if the company name exists in the repository list.
    
    Returns the company name (as the identifier) if found, otherwise None.
    Raises RuntimeError on critical failure to fetch the list.
    """
    try:
        # Assuming companies is a list of strings (names)
        companies: List[str] = get_all_companies()
        if company_name in companies:
            return company_name
        return None
    except Exception as e:
        print(f"CRITICAL: Failed to fetch companies list: {e}")
        # Raise RuntimeError to be caught by the FastAPI route
        raise RuntimeError("Billing initialization failed due to repository error.")


def generate_invoice_for_single_company(company_name: str, month: int, year: int) -> Dict[str, Any] | None:
    """
    Generates an invoice for a single company based on its name, 
    creates PDF/CSV, and emails it. Returns the invoice data on success.
    """
    
    # 1. Check Company Existance and Retrieve Identifier (which is the name)
    try:
        # The returned identifier will be the company name string itself
        company_id = _get_company_name_if_exists(company_name)
    except RuntimeError as e:
        print(f"Fatal error during company lookup: {e}")
        return None # Signal critical failure back to the route handler
        
    if not company_id:
        print(f"Warning: Company '{company_name}' not found in the database. Skipping generation.")
        return None
    
    
    try:
        # 2. Generate/Fetch invoice data (using company ID/Name)
        invoice_data = generate_monthly_bill(company_id, month, year)
        
        # Check if the billing service returned data
        if not invoice_data:
             print(f"Billing service returned no data for {company_name} (ID: {company_id}).")
             return None

        # --- DETERMINE CSV PATH ---
        billing_period = invoice_data.get('billingPeriod', {})
        start_date = billing_period.get('startDate')
        end_date = billing_period.get('endDate')

        print("Timezone for the company is:", invoice_data.get('tzone'))

        invoice_data = localize_datetime_fields(invoice_data, invoice_data.get('tzone'))

        # The invoice_data should contain "invoice_number"
        pdf_path = generate_invoice_pdf(invoice_data)
        
        csv_path = None
        # We use the company_id (which is the name string) to construct the path
        if start_date and end_date:
            csv_path = _construct_csv_filepath(company_id, start_date, end_date)
        # --------------------------
        
        # --- SEND EMAIL ---
        company_info = invoice_data.get('companyInfo', {})
        # recipient_email = company_info.get('billingEmail')
        recipient_email = "vishruth.ramesh@vysedeck.com" 
        company_name_from_data = company_info.get('legalName')
        invoice_number = invoice_data.get('invoice_number')

        # Ensure we have the critical data before attempting to send the email
        if recipient_email and company_name_from_data and invoice_number and csv_path: 
            send_invoice_email(
                recipient_email=recipient_email,
                company_name=company_name_from_data,
                invoice_number=invoice_number,
                pdf_path=pdf_path,
                csv_path=csv_path, # <-- Pass the constructed CSV path
                invoice_data=invoice_data
            )
            print(f"Invoice and Call Log CSV mailed for {company_name} (ID: {invoice_number}): {pdf_path}")
        else:
            missing_fields = []
            if not recipient_email: missing_fields.append('recipient_email')
            if not company_name_from_data: missing_fields.append('company_name')
            if not invoice_number: missing_fields.append('invoice_number')
            if not csv_path: missing_fields.append('csv_path (check billingPeriod dates)')
            print(f"Skipping email for {company_name}. Missing critical data: {', '.join(missing_fields)}.")
            
        # Return the structured data which should conform to InvoiceModel
        return invoice_data
            
    except Exception as e:
        print(f"Failed to process or mail invoice for {company_name}: {e}")
        return None
