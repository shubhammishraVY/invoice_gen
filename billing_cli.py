from services.invoice_service import generate_invoices_for_all
from repositories.companies_repo import get_all_companies
from datetime import datetime

if __name__ == "__main__":
    now = datetime.now()
    last_month = now.month - 1 if now.month > 1 else 12
    year = now.year if now.month > 1 else now.year - 1
    
    # Fetch companies from the repository for dynamic execution
    try:
        # companies = get_all_companies() 
        companies = ["webxpress"]
    except Exception as e:
        print(f"CRITICAL: Failed to fetch companies list: {e}")
        # Exit with an error code if initialization fails
        exit(1)


    if not companies:
        print("No companies found to process. Job skipped.")
    else:
        print(f"Starting scheduled invoice generation for {len(companies)} companies for {last_month}/{year}...")
        try:
            generate_invoices_for_all(companies=companies, month=last_month, year=year)
            print("✅ Job completed successfully.")
        except Exception as e:
            print(f"❌ Job failed unexpectedly during processing: {e}")