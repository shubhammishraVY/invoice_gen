from services.billing_service import generate_monthly_bill
from services.pdf_service import generate_invoice_pdf
from services.mailer_service import send_invoice_email 

def generate_invoices_for_all(companies: list[str], month: int, year: int):
    """Generate invoices for all companies, create PDFs, and email them."""
    generated_pdfs = []
    for company in companies:
        try:
            # 1. Generate/Fetch invoice data (including saving to DB)
            invoice_data = generate_monthly_bill(company, month, year)
            
            # The invoice_data now contains "invoice_number"
            pdf_path = generate_invoice_pdf(invoice_data)
            
            # --- NEW STEP: SEND EMAIL ---
            # Retrieve necessary client details from the invoice data
            company_info = invoice_data.get('companyInfo', {})
            recipient_email = company_info.get('billingEmail')
            company_name = company_info.get('legalName')
            invoice_number = invoice_data.get('invoice_number')

            # Ensure we have the critical data before attempting to send the email
            if recipient_email and company_name and invoice_number:
                send_invoice_email(
                    recipient_email=recipient_email,
                    company_name=company_name,
                    invoice_number=invoice_number,
                    pdf_path=pdf_path,
                    invoice_data=invoice_data
                )
                print(f"Invoice generated and mailed for {company} (ID: {invoice_number}): {pdf_path}")
            else:
                print(f"Skipping email for {company}. Missing recipient_email, company_name, or invoice_number in invoice_data.")
            
            generated_pdfs.append({"company": company, "pdf": pdf_path})
            
        except Exception as e:
            print(f"Failed to process or mail invoice for {company}: {e}")
            
    return generated_pdfs
