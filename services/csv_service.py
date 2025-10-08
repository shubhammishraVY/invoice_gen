import csv
from datetime import datetime
import os
import math
from typing import List, Dict, Any
from utils.date_utils import _get_date_format_for_tz
import pendulum # Import pendulum for parsing and formatting

def generate_call_log_csv(
    company_id: str, 
    calls_top: List[Dict[str, Any]], 
    calls_nested: List[Dict[str, Any]], 
    start_date: datetime, 
    end_date: datetime,
    total_minutes: int, # New parameter: Total billed minutes
    total_calls: int, # New parameter: Total number of calls
    target_timezone: str # New parameter: Timezone for date formatting
) -> str:
    """
    Generates a multi-section CSV file containing:
    1. A header row.
    2. A summary row of total calls and total billed minutes, including the Assistant Phone Number.
    3. Detailed call logs with calculated billed minutes (rounded up), with dates formatted 
       according to the target_timezone's regional convention (without applying timezone offset).

    Args:
        company_id: The ID of the company.
        calls_top: List of call log dictionaries from the top-level collection.
        calls_nested: List of call log dictionaries from the nested collection.
        start_date: Start date of the billing period (used for file naming).
        end_date: End date of the billing period (used for file naming).
        total_minutes: The total billed minutes for the period.
        total_calls: The total number of calls for the period.
        target_timezone: The timezone string (e.g., 'Asia/Kolkata') to determine date format.

    Returns:
        The file path of the generated CSV file. Returns an empty string on failure.
    """


    print("************ Calling the GENERATE CSV Function **********")

    all_calls = calls_top + calls_nested
    
    # Extract the Assistant Phone No. from the first call (assuming it's consistent)
    assistant_phone = all_calls[0].get("assistant_phone", "N/A") if all_calls else "N/A"
    assistant_phone = f"'{assistant_phone}" if assistant_phone else ""

    # --- DATE FORMATTING SETUP ---
    # Determine the date format string (e.g., '%d-%m-%Y') based on the target timezone
    # We will append time formatting to this date format.
    DATE_ONLY_FORMAT = _get_date_format_for_tz(target_timezone)
    # The CSV needs date and time, so we combine the date format with a standard time format.
    DATETIME_FORMAT = f"{DATE_ONLY_FORMAT} %H:%M:%S"
    
    def format_log_datetime(dt_iso_string: str) -> str:
        """
        Formats an ISO date string into the determined regional format (Date and Time),
        without applying any timezone offset.
        """
        if not dt_iso_string:
            return ""
        try:
            # Parse the ISO string, assuming it represents the target date in UTC.
            # We use 'UTC' as the assumed timezone for the *value* so we don't shift it.
            dt_obj = pendulum.parse(dt_iso_string, tz='UTC')
            
            # Format the original date and time components using the determined regional format.
            return dt_obj.strftime(DATETIME_FORMAT)
        except Exception:
            # Return original string if parsing fails
            return dt_iso_string
    # --- END DATE FORMATTING SETUP ---


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

    # Create a descriptive filename using the billing period (using YYYY-MM-DD for file name consistency)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    filename = f"{company_id}_call_logs_{start_str}_to_{end_str}.csv"
    filepath = os.path.join(output_dir, filename)

    print(f"Attempting to generate call log CSV at: {filepath}")

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 1. Write the Heading Row
            writer.writerow([f"Call Logs Details for {company_id} from {start_date.strftime(DATE_ONLY_FORMAT)} to {end_date.strftime(DATE_ONLY_FORMAT)}"])
            writer.writerow([]) 

            # 2. Write the Summary Header and Values
            summary_headers = ["Total_Calls", "Total Billed Minutes", "Assistant_Phone_No"]
            summary_values = [total_calls, total_minutes, assistant_phone]
            
            padding_count = len(detail_fieldnames) - len(summary_headers)
            writer.writerow(summary_headers + [""] * padding_count)
            writer.writerow(summary_values + [""] * padding_count)
            writer.writerow([]) 
            
            # Now, use DictWriter for the detailed log section
            detail_writer = csv.DictWriter(csvfile, fieldnames=detail_fieldnames)
            
            # 3. Write the detailed log header
            detail_writer.writeheader()
            
            # 4. Write the detailed log rows
            for call in all_calls:
                duration_secs = call.get("duration", 0)
                
                # Calculate billed minutes: ceiling of duration / 60
                billed_mins = math.ceil(duration_secs / 60)
                
                # Prepend phone number with a single quote to prevent Excel scientific notation/truncation
                customer_phone_str = str(call.get("customer_phone", ""))
                safe_customer_phone = f"'{customer_phone_str}" if customer_phone_str else "" 

                # Extract raw date values
                received_at_raw = call.get("receivedAt", call.get("received_at", ""))
                finished_at_raw = call.get("finished_at", "")
                created_at_raw = call.get("created_at", "")
                
                # Convert any remaining datetime objects to ISO strings first for consistency
                # and then format the ISO string
                if isinstance(received_at_raw, datetime): received_at_raw = received_at_raw.isoformat()
                if isinstance(finished_at_raw, datetime): finished_at_raw = finished_at_raw.isoformat()
                if isinstance(created_at_raw, datetime): created_at_raw = created_at_raw.isoformat()

                # --- APPLY FORMATTING HERE ---
                row = {
                    "id": call.get("id"), 
                    "Customer_Phone": safe_customer_phone,
                    "Duration [in secs]": duration_secs,
                    "In mins [rounded-off]": billed_mins,
                    "Received_At": format_log_datetime(received_at_raw),
                    "Finished_At": format_log_datetime(finished_at_raw),
                    "Created_At": format_log_datetime(created_at_raw),
                }

                detail_writer.writerow(row)
        
        print(f"Successfully generated CSV for {company_id}: {filepath}")
        return filepath

    except Exception as e:
        print(f"Error generating CSV for {company_id}: {e}")
        return ""