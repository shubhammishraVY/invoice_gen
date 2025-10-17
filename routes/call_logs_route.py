from fastapi import APIRouter, HTTPException, Query
from services.call_logs_service import get_call_logs_for_company

router = APIRouter()

@router.get("/call-logs/{company_id}")
def get_company_call_logs(
    company_id: str,
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DD)")
):
    """
    Fetch call logs for a company within the specified date range.
    This endpoint is intended for internal services to consume call log data.
    """
    try:
        result = get_call_logs_for_company(company_id, start_date, end_date)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch call logs: {e}")
