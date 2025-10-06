import csv
from datetime import datetime
import os
from typing import List, Dict, Any

def generate_call_log_csv(
    company_id: str, 
    calls_top: List[Dict[str, Any]], 
    calls_nested: List[Dict[str, Any]], 
    start_date: datetime, 
    end_date: datetime
) -> str:
    """
    Generates a CSV file containing combined call logs for a company and saves it locally.

    The columns generated are: id (docId), assistant_phone, call_type, customer_phone, 
    created_at, duration (in secs), finished_at, receivedAt.

    Args:
        company_id: The ID of the company.
        calls_top: List of call log dictionaries from the top-level collection.
        calls_nested: List of call log dictionaries from the nested collection.
        start_date: Start date of the billing period (used for file naming).
        end_date: End date of the billing period (used for file naming).

    Returns:
        The file path of the generated CSV file. Returns an empty string on failure.
    """


    print("************ Calling the GENERATE CSV Function **********")

    all_calls = calls_top + calls_nested
    
    # Define CSV columns as requested by the user
    fieldnames = [
        "id", 
        "assistant_phone", 
        "call_type", 
        "customer_phone", 
        "created_at", 
        "duration (in secs)", 
        "finished_at", 
        "receivedAt"
    ]
    
    # Prepare the output directory (invoices/)
    output_dir = "invoices"
    os.makedirs(output_dir, exist_ok=True)

    # Create a descriptive filename using the billing period
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filename = f"{company_id}_call_logs_{start_str}_to_{end_str}.csv"
    filepath = os.path.join(output_dir, filename)

    print(f"Attempting to generate call log CSV at: {filepath}")

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for call in all_calls:
                # Map Firestore document keys to CSV column headers
                row = {
                    # Assuming the document ID is passed as 'id' or 'docId' from the repository
                    "id": call.get("id") or call.get("docId", ""), 
                    "assistant_phone": call.get("assistant_phone", ""),
                    "call_type": call.get("call_type", ""),
                    "customer_phone": call.get("customer_phone", ""),
                    "created_at": call.get("created_at", ""),
                    "duration (in secs)": call.get("duration", 0),
                    "finished_at": call.get("finished_at", ""),
                    "receivedAt": call.get("receivedAt", "")
                }
                
                # Convert any remaining datetime objects to ISO strings for consistent CSV output
                for key in ["created_at", "finished_at", "receivedAt"]:
                    value = row.get(key)
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()

                writer.writerow(row)
        
        print(f"Successfully generated CSV for {company_id}: {filepath}")
        return filepath

    except Exception as e:
        print(f"Error generating CSV for {company_id}: {e}")
        return ""