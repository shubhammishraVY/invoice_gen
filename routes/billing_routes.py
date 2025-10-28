from fastapi import APIRouter, Query, HTTPException, status
from services.invoice_service_copy import generate_invoice_for_company
from typing import Dict, Any

router = APIRouter()


@router.post("/generate")
def generate_invoice(
    companyId: str = Query(..., description="Company ID (use 'vysedeck' for main entity)"),
    tenantId: str = Query(..., description="Tenant ID (same as companyId if main entity, otherwise sub-entity ID)"),
    month: int | None = Query(None, description="Month (1-12). Defaults to last completed month"),
    year: int | None = Query(None, description="Year. Defaults to current year if not provided")
) -> Dict[str, Any]:
    """
    Generates an invoice for either:
    1. Main entity: when companyId == 'vysedeck' (not a sub-entity relationship)
    2. Sub-entity: when companyId != 'vysedeck' (tenantId is a sub-entity)
    
    The invoice is generated, PDF and CSV are created, and an email is sent.
    
    Returns the generated invoice data on success.
    """
    
    print(f"📨 Received invoice request for companyId={companyId}, tenantId={tenantId}, period={month}/{year}")
    
    try:
        # The service will automatically determine if this is a sub-entity relationship
        # based on whether companyId == "vysedeck"
        
        # Call the unified invoice generation function
        invoice_data = generate_invoice_for_company(
            company_id=companyId,
            tenant_id=tenantId,
            month=month,
            year=year
        )
        
        # Check if invoice generation was successful
        if not invoice_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice generation failed: No billing data found for the specified parameters."
            )
        
        print("✅ Invoice generation and mailing completed successfully")
        return invoice_data
        
    except ValueError as ve:
        # Handle specific billing service errors (like future date validation)
        print(f"⚠️ Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ Invoice generation failed unexpectedly: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during invoice generation: {str(e)}"
        )


@router.get("/invoice/{invoice_id}")
def get_invoice_by_id(invoice_id: str) -> Dict[str, Any]:
    """
    Retrieves an existing invoice by its ID.
    """
    from repositories.bill_repo import get_invoice_by_id
    
    try:
        invoice = get_invoice_by_id(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found"
            )
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving invoice {invoice_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve invoice: {str(e)}"
        )