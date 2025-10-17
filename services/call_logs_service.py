from datetime import datetime
from repositories.callLogs_repo import (
    get_calls_from_top_level,
    get_calls_from_company_doc
)

def get_call_logs_for_company(company_id: str, start_date: str, end_date: str):
    """
    Fetch call logs for a given company between start_date and end_date.

    Args:
        company_id: The ID of the company.
        start_date: ISO date string (YYYY-MM-DD)
        end_date: ISO date string (YYYY-MM-DD)
    """
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Fetch both top-level and nested calls if needed
        calls_top = get_calls_from_top_level(company_id, start_dt, end_dt)
        calls_nested = get_calls_from_company_doc(company_id, start_dt, end_dt)

        all_calls = calls_top + calls_nested
        all_calls.sort(key=lambda x: x.get("receivedAt"), reverse=True)

        return {"company_id": company_id, "total_calls": len(all_calls), "calls": all_calls}

    except Exception as e:
        print(f"❌ Error fetching call logs for {company_id}: {e}")
        return {"company_id": company_id, "error": str(e)}
