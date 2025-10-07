import csv
from datetime import datetime
import os
import math
from typing import List, Dict, Any

def generate_call_log_csv(
    company_id: str, 
    calls_top: List[Dict[str, Any]], 
    calls_nested: List[Dict[str, Any]], 
    start_date: datetime, 
    end_date: datetime,
    total_minutes: int, # New parameter: Total billed minutes
    total_calls: int    # New parameter: Total number of calls
) -> str:
    """
    Generates a multi-section CSV file containing:
    1. A header row.
    2. A summary row of total calls and total billed minutes, including the Assistant Phone Number.
    3. Detailed call logs with calculated billed minutes (rounded up).

    Args:
        company_id: The ID of the company.
        calls_top: List of call log dictionaries from the top-level collection.
        calls_nested: List of call log dictionaries from the nested collection.
        start_date: Start date of the billing period (used for file naming).
        end_date: End date of the billing period (used for file naming).
        total_minutes: The total billed minutes for the period.
        total_calls: The total number of calls for the period.

    Returns:
        The file path of the generated CSV file. Returns an empty string on failure.
    """


    print("************ Calling the GENERATE CSV Function **********")

    all_calls = calls_top + calls_nested
    
    # Extract the Assistant Phone No. from the first call (assuming it's consistent)
    # Default to "N/A" if the calls list is empty or the field is missing
    assistant_phone = all_calls[0].get("assistant_phone", "N/A") if all_calls else "N/A"
    assistant_phone = f"'{assistant_phone}" if assistant_phone else ""

    # Define the field names for the detailed call log section
    detail_fieldnames = [
        "id", 
        "Customer_Phone", 
        "Duration [in secs]", 
        "In mins [rounded-off]", 
        "Received_At", 
        "Finished_At", 
        "Created_At"
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
            # Use a regular CSV writer for the custom header and summary rows
            writer = csv.writer(csvfile)
            
            # 1. Write the Heading Row
            writer.writerow([f"Call Logs Details for {company_id} from {start_date} to {end_date}"])
            writer.writerow([]) # Empty row for visual separation

            # 2. Write the Summary Header and Values
            summary_headers = ["Total_Calls", "Total Billed Minutes", "Assistant_Phone_No"]
            summary_values = [total_calls, total_minutes, assistant_phone]
            
            # Write the summary headers, followed by empty cells to align with detail columns
            padding_count = len(detail_fieldnames) - len(summary_headers)
            writer.writerow(summary_headers + [""] * padding_count)
            writer.writerow(summary_values + [""] * padding_count)
            writer.writerow([]) # Empty row for visual separation
            
            # Now, use DictWriter for the detailed log section
            detail_writer = csv.DictWriter(csvfile, fieldnames=detail_fieldnames)
            
            # 3. Write the detailed log header
            detail_writer.writeheader()
            
            # 4. Write the detailed log rows
            for call in all_calls:
                duration_secs = call.get("duration", 0)
                
                # Calculate billed minutes: ceiling of duration / 60
                # Billed minutes = ceiling(duration / 60)
                billed_mins = math.ceil(duration_secs / 60)
                
                # Prepend phone number with a single quote to prevent Excel scientific notation/truncation
                customer_phone_str = str(call.get("customer_phone", ""))
                # Only prepend quote if the number is not empty
                safe_customer_phone = f"'{customer_phone_str}" if customer_phone_str else "" 

                row = {
                    "id": call.get("id"), 
                    "Customer_Phone": safe_customer_phone,
                    "Duration [in secs]": duration_secs,
                    "In mins [rounded-off]": billed_mins,
                    # Note: Using the raw field names from Firestore keys
                    "Received_At": call.get("receivedAt", ""),
                    "Finished_At": call.get("finished_at", ""),
                    "Created_At": call.get("created_at", ""),
                }
                
                # Convert any remaining datetime objects to ISO strings for consistent CSV output
                for key in ["Created_At", "Finished_At", "Received_At"]:
                    value = row.get(key)
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                    # Handle possible Firestore Timestamps if they weren't converted earlier
                    elif hasattr(value, 'to_iso_str'): 
                        row[key] = value.to_iso_str()

                detail_writer.writerow(row)
        
        print(f"Successfully generated CSV for {company_id}: {filepath}")
        return filepath

    except Exception as e:
        print(f"Error generating CSV for {company_id}: {e}")
        return ""