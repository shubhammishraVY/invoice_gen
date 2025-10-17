# from fastapi import APIRouter, Query, HTTPException, status
# # Import the renamed single-company function
# from services.invoice_service_copy import generate_invoice_for_single_company 
# from reqResVal_models.billing_models import InvoiceModel
# from typing import Dict, Any

# router = APIRouter()

# @router.post("/generate/{company_name}", response_model=InvoiceModel)
# def generate_bill_for_company(
#     # Use Query parameter for the company name
#     company_name: str ,
#     month: int | None = Query(None, description="Month (1-12). Defaults to last completed month"),
#     year: int | None = Query(None, description="Year. Defaults to current year if not provided")
# ) -> Dict[str, Any]:
#     """
#     Triggers the generation, PDF creation, CSV attachment, and mailing of a 
#     single invoice for a company identified by its name for the given period.
    
#     Returns the generated InvoiceModel data on success.
#     """
    
#     print(f"Received single invoice request for {company_name} for {month}/{year}.")
    
#     try:
#         # Call the single-company generation function
#         invoice_data = generate_invoice_for_single_company(company_name, month, year)
        
#         if invoice_data is None:
#             # This covers: Company not found, or Billing service returned no data.
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, 
#                 detail=f"Invoice generation failed: Company '{company_name}' not found or bill data could not be generated."
#             )
        
#         # FastAPI uses response_model=InvoiceModel to automatically validate 
#         # the returned 'invoice_data' dictionary against the Pydantic model.
#         print("✅ Job completed successfully.")
#         return invoice_data
        
#     except HTTPException:
#         # Re-raise the 404/other HTTP exceptions
#         raise
#     except RuntimeError as e:
#         # Catch errors from the repository layer (e.g., get_all_companies failed)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"CRITICAL SYSTEM ERROR during initialization: {e}"
#         )
#     except Exception as e:
#         print(f"❌ Job failed unexpectedly during processing: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="An unexpected error occurred during invoice generation."
#         )
