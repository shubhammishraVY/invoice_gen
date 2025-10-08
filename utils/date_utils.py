import pendulum
from datetime import datetime
from typing import Dict, Any

# Define explicit format rules based on the regional intent of the user's files.
# This ensures that date fields like Invoice Date and Due Date use the required regional format.

# DD-MM-YYYY (Day-Month-Year) is common in India (Asia/Kolkata) and Europe/UK.
# MM-DD-YYYY (Month-Day-Year) is common in the US (America/*).
# YYYY-MM-DD (ISO Style) is used for UTC and generic timezones.
TIMEZONE_DATE_FORMAT_MAP = {
    # India / Asia / Europe / UK (DD-MM-YYYY format) - Most of the world
    "DD_MM_YYYY": [
        "Asia/Kolkata", "Asia/Calcutta", "Asia/Mumbai", "Asia/Delhi", "Asia/Colombo",
        "Europe/London", "Europe/Dublin", "Europe/Paris", "Europe/Berlin", "Europe", "Asia",
    ],
    # US / North America (MM-DD-YYYY format)
    "MM_DD_YYYY": [
        "America/New_York", "America/Los_Angeles", "America/Chicago", "America/Denver", 
        "America/Phoenix", "America/Anchorage", "America/Honolulu", "America", "US"
    ],
    # ISO Standard (YYYY-MM-DD format) - For UTC and generic timezones
    "ISO_STYLE": [
        "UTC", "Etc/GMT", "Etc/GMT+0", "Etc/GMT-0"
    ]
}

# Map keys to the actual Python strftime format strings
FORMAT_STRINGS = {
    "DD_MM_YYYY": "%d-%m-%Y", # e.g., 30-09-2025
    "MM_DD_YYYY": "%m-%d-%Y",  # e.g., 09-30-2025
    "ISO_STYLE": "%Y-%m-%d"    # e.g., 2025-09-30
}

def _get_date_format_for_tz(target_tz_str: str) -> str:
    """Determines the appropriate date format string based on the timezone prefix."""
    
    # Prioritize specific city/region matches
    for style, zones in TIMEZONE_DATE_FORMAT_MAP.items():
        for zone_prefix in zones:
            if target_tz_str.startswith(zone_prefix):
                return FORMAT_STRINGS[style]
    
    # Default to the DD-MM-YYYY style if no specific match is found
    # This is a sensible default as it is widely used (e.g., India, Europe).
    return FORMAT_STRINGS["DD_MM_YYYY"]


def localize_datetime_fields(data: Dict[str, Any], target_tz_str: str) -> Dict[str, Any]:
    """
    Recursively formats all datetime-like strings or objects using the 
    DATE format dictated by the target timezone, but without changing the
    day/month/year value due to timezone offsets.
    """
    
    # 1. Prepare the Target Timezone and Date Format
    try:
        # We need this to determine the format, but won't use it for conversion
        pendulum.timezone(target_tz_str)
    except Exception:
        # Fallback to Asia/Kolkata if the provided TZ is invalid
        print(f"Warning: Invalid timezone '{target_tz_str}'. Defaulting to Asia/Kolkata.")
        target_tz_str = 'Asia/Kolkata' 
        
    DATE_FORMAT = _get_date_format_for_tz(target_tz_str)
    
    # 2. Recursion Helper Function
    def _process(item):
        if isinstance(item, dict):
            # Recurse through dictionary items
            return {k: _process(v) for k, v in item.items()}
        
        elif isinstance(item, list):
            # Recurse through list items
            return [_process(element) for element in item]
        
        elif isinstance(item, str):
            # Attempt to parse ISO strings into datetime objects
            try:
                # Parse the ISO string, assuming it represents the target date in UTC.
                dt_obj = pendulum.parse(item, tz='UTC') 
                
                # Format the original date components (Y, M, D) using the determined regional format,
                # WITHOUT performing any timezone conversion (which would change the day).
                return dt_obj.strftime(DATE_FORMAT)
                
            except Exception:
                # If parsing fails, it's just a regular string, return it as is
                return item
        
        elif isinstance(item, (datetime, pendulum.DateTime)):
            # Handle actual datetime objects passed directly (e.g., from DB repos)
            
            # Convert to pendulum object, assuming UTC if timezone-naive
            if isinstance(item, datetime):
                # Ensure it's timezone aware for consistency, assuming UTC is correct
                dt_obj = pendulum.instance(item, tz='UTC') 
            else:
                dt_obj = item # Already a pendulum object

            # Format the original date components (Y, M, D) using the determined regional format,
            # WITHOUT performing any timezone conversion.
            return dt_obj.strftime(DATE_FORMAT) 
        
        else:
            return item
    
    return _process(data)
