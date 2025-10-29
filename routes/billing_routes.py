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


@router.post("/update-overdue-invoices")
def update_overdue_invoices_endpoint(
    company_id: str | None = Query(None, description="Optional: Specific company ID to update"),
    tenant_id: str | None = Query(None, description="Optional: Specific tenant ID to update")
) -> Dict[str, Any]:
    """
    Updates all pending invoices that are past their due date to 'due' status.
    
    - If company_id is provided, updates only that company's invoices
    - If company_id and tenant_id are provided, updates only that tenant's invoices
    - If neither is provided, updates all companies
    
    This endpoint can be called:
    1. Manually when needed
    2. By a scheduled task/cron job (recommended: daily)
    3. Before generating reports
    """
    from repositories.bill_repo import update_overdue_invoices, update_all_overdue_invoices
    
    try:
        if company_id:
            # Update specific company or tenant
            result = update_overdue_invoices(company_id, tenant_id)
            return {
                "status": "success",
                "scope": f"company: {company_id}" + (f", tenant: {tenant_id}" if tenant_id else ""),
                **result
            }
        else:
            # Update all companies
            result = update_all_overdue_invoices()
            return {
                "status": "success",
                "scope": "all companies",
                **result
            }
    except Exception as e:
        print(f"❌ Error updating overdue invoices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update overdue invoices: {str(e)}"
        )