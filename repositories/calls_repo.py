from db_configs.firebase_db import firestore_client
from datetime import datetime
from google.cloud.firestore import Query

def get_calls_from_top_level(company_id: str, start_date: datetime, end_date: datetime):
    """Fetch calls from top-level `calls` collection."""
    calls_ref = firestore_client.collection("calls")
    query = (calls_ref
            .where("companyId", "==", company_id)
            .where("receivedAt", ">=", start_date)
            .where("receivedAt", "<=", end_date)
            .order_by("receivedAt", direction=Query.DESCENDING)
            .order_by(firestore_client.field_path('__name__'), direction=Query.DESCENDING))
    
    return [doc.to_dict() for doc in query.stream()]

def get_calls_from_company_doc(company_id: str, start_date: datetime, end_date: datetime):
    """Fetch calls from nested `companies/{company}/calls` collection."""
    calls_ref = firestore_client.collection("companies").document(company_id).collection("calls")
    query = (calls_ref
            .where("receivedAt", ">=", start_date)
            .where("receivedAt", "<=", end_date)
            .order_by("receivedAt", direction=Query.DESCENDING)
            .order_by(firestore_client.field_path('__name__'), direction=Query.DESCENDING))
    
    return [doc.to_dict() for doc in query.stream()]
