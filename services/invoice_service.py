#This file is used by the billing_cli.py script to run
from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_invoice_pdf
from services.mailer_service import send_invoice_email 
from datetime import datetime # Import datetime for path construction
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


def generate_invoices_for_all(companies: list[str], month: int, year: int):
    """Generate invoices for all companies, create PDFs, attach CSV and email them."""
    generated_pdfs = []
    for company in companies:
        try:
            # 1. Generate/Fetch invoice data (including saving to DB)
            invoice_data = generate_monthly_bill(company, month, year)
            
            # Retrieve billing dates from the raw invoice data ( not the localized one )
            billing_period = invoice_data.get('billingPeriod', {})
            start_date = billing_period.get('startDate')
            end_date = billing_period.get('endDate')

            print("Timezone for the company is:", invoice_data.get('tzone'))

            invoice_data = localize_datetime_fields(invoice_data, invoice_data.get('tzone'))

            # The invoice_data now contains "invoice_number"
            pdf_path = generate_invoice_pdf(invoice_data)
            
            csv_path = None
            if start_date and end_date:
                # Construct the path to the expected CSV file in the 'invoices' folder.
                csv_path = _construct_csv_filepath(company, start_date, end_date)
            # --------------------------------------
            
            # --- SEND EMAIL ---
            # Retrieve necessary client details from the invoice data
            company_info = invoice_data.get('companyInfo', {})
            # recipient_email = company_info.get('billingEmail')
            recipient_email = "vishruth.ramesh@vysedeck.com" 
            company_name = company_info.get('legalName')
            invoice_number = invoice_data.get('invoice_number')

            # Ensure we have the critical data before attempting to send the email
            if recipient_email and company_name and invoice_number and csv_path: 
                send_invoice_email(
                    recipient_email=recipient_email,
                    company_name=company_name,
                    invoice_number=invoice_number,
                    pdf_path=pdf_path,
                    csv_path=csv_path, # <-- Pass the constructed CSV path
                    invoice_data=invoice_data
                )
                print(f"Invoice and Call Log CSV mailed for {company} (ID: {invoice_number}): {pdf_path}")
            else:
                missing_fields = []
                if not recipient_email: missing_fields.append('recipient_email')
                if not company_name: missing_fields.append('company_name')
                if not invoice_number: missing_fields.append('invoice_number')
                if not csv_path: missing_fields.append('csv_path (check billingPeriod dates)')
                print(f"Skipping email for {company}. Missing critical data: {', '.join(missing_fields)}.")
            
            generated_pdfs.append({"company": company, "pdf": pdf_path, "csv": csv_path})
            
        except Exception as e:
            print(f"Failed to process or mail invoice for {company}: {e}")
            
    return generated_pdfs
