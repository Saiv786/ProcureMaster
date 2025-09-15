import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union
import re

def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    phone_pattern = r'^[\+]?[1-9]?[\d\s\-\(\)]{7,15}$'
    return re.match(phone_pattern, phone.strip()) is not None

def format_currency(amount: Union[int, float], currency_symbol: str = "$") -> str:
    """Format amount as currency"""
    if amount is None:
        return f"{currency_symbol}0.00"
    return f"{currency_symbol}{amount:,.2f}"

def format_date(date_obj: Union[date, datetime, str], format_str: str = "%Y-%m-%d") -> str:
    """Format date object to string"""
    if date_obj is None:
        return "Not set"
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
        except ValueError:
            return date_obj
    
    if isinstance(date_obj, datetime):
        return date_obj.strftime(format_str)
    elif isinstance(date_obj, date):
        return date_obj.strftime(format_str)
    
    return str(date_obj)

def format_datetime(datetime_obj: Union[datetime, str], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    if datetime_obj is None:
        return "Not set"
    
    if isinstance(datetime_obj, str):
        try:
            datetime_obj = datetime.strptime(datetime_obj, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime_obj
    
    if isinstance(datetime_obj, datetime):
        return datetime_obj.strftime(format_str)
    
    return str(datetime_obj)

def calculate_progress_percentage(current: Union[int, float], target: Union[int, float]) -> float:
    """Calculate progress percentage"""
    if target is None or target == 0:
        return 0.0
    
    if current is None:
        current = 0
    
    return min((current / target) * 100, 100.0)

def calculate_days_between(start_date: Union[date, datetime, str], end_date: Union[date, datetime, str]) -> int:
    """Calculate number of days between two dates"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    return (end_date - start_date).days

def is_overdue(due_date: Union[date, datetime, str], current_date: Optional[date] = None) -> bool:
    """Check if a date is overdue"""
    if due_date is None:
        return False
    
    if current_date is None:
        current_date = date.today()
    
    if isinstance(due_date, str):
        due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
    elif isinstance(due_date, datetime):
        due_date = due_date.date()
    
    return due_date < current_date

def get_status_color(status: str) -> str:
    """Get color emoji for status"""
    status_colors = {
        # Work Order statuses
        "Pending": "🔴",
        "In Progress": "🟡",
        "Completed": "🟢",
        "Dispatched": "🔵",
        
        # Cutting statuses
        "Cut": "🟢",
        "Re-cut": "🟡",
        
        # Priority levels
        "High": "🔴",
        "Medium": "🟡",
        "Low": "🟢",
        
        # Target statuses
        "Not Started": "🔴",
        
        # Dispatch statuses
        "In Transit": "🔵",
        "Delivered": "🟢",
        "Delayed": "🔴",
        
        # General statuses
        "Active": "🟢",
        "Inactive": "🔴",
        "On Hold": "🟡"
    }
    
    return status_colors.get(status, "⚪")

def get_priority_order(priority: str) -> int:
    """Get numeric order for priority sorting"""
    priority_order = {
        "High": 3,
        "Medium": 2,
        "Low": 1
    }
    return priority_order.get(priority, 0)

def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if text is None:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def safe_divide(numerator: Union[int, float], denominator: Union[int, float], default: Union[int, float] = 0) -> float:
    """Safely divide two numbers, return default if denominator is zero"""
    if denominator == 0 or denominator is None:
        return default
    
    if numerator is None:
        numerator = 0
    
    return numerator / denominator

def generate_wo_number(prefix: str = "WO", date_obj: Optional[date] = None) -> str:
    """Generate work order number"""
    if date_obj is None:
        date_obj = date.today()
    
    date_str = date_obj.strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%H%M%S")
    
    return f"{prefix}-{date_str}-{timestamp}"

def generate_order_number(prefix: str = "ORD", date_obj: Optional[date] = None) -> str:
    """Generate order number"""
    if date_obj is None:
        date_obj = date.today()
    
    date_str = date_obj.strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%H%M%S")
    
    return f"{prefix}-{date_str}-{timestamp}"

def parse_dimensions(dimension_string: str) -> Dict[str, float]:
    """Parse dimension string like '100x200' into width and height"""
    try:
        if 'x' in dimension_string.lower():
            parts = dimension_string.lower().split('x')
            if len(parts) == 2:
                return {
                    'width': float(parts[0].strip()),
                    'height': float(parts[1].strip())
                }
    except ValueError:
        pass
    
    return {'width': 0.0, 'height': 0.0}

def calculate_area(width: Union[int, float], height: Union[int, float]) -> float:
    """Calculate area from width and height"""
    if width is None or height is None:
        return 0.0
    
    return float(width) * float(height)

def validate_positive_number(value: Union[int, float, str], field_name: str = "Value") -> bool:
    """Validate that a value is a positive number"""
    try:
        num_value = float(value)
        if num_value <= 0:
            st.error(f"{field_name} must be greater than 0")
            return False
        return True
    except (ValueError, TypeError):
        st.error(f"{field_name} must be a valid number")
        return False

def validate_date_range(start_date: date, end_date: date, allow_same_day: bool = True) -> bool:
    """Validate that end date is after start date"""
    if start_date is None or end_date is None:
        return True
    
    if allow_same_day:
        if end_date < start_date:
            st.error("End date cannot be before start date")
            return False
    else:
        if end_date <= start_date:
            st.error("End date must be after start date")
            return False
    
    return True

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"

def clean_string(text: str, remove_extra_spaces: bool = True) -> str:
    """Clean and normalize string input"""
    if text is None:
        return ""
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove extra spaces
    if remove_extra_spaces:
        text = re.sub(r'\s+', ' ', text)
    
    return text

def format_list_display(items: List[str], max_items: int = 3, separator: str = ", ") -> str:
    """Format list for display with truncation"""
    if not items:
        return "None"
    
    if len(items) <= max_items:
        return separator.join(items)
    
    displayed_items = items[:max_items]
    remaining_count = len(items) - max_items
    
    return f"{separator.join(displayed_items)} and {remaining_count} more"

def get_week_dates(date_obj: Optional[date] = None) -> Dict[str, date]:
    """Get start and end dates of the week for given date"""
    if date_obj is None:
        date_obj = date.today()
    
    # Monday is 0, Sunday is 6
    days_since_monday = date_obj.weekday()
    monday = date_obj - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    
    return {
        'start': monday,
        'end': sunday
    }

def get_month_dates(date_obj: Optional[date] = None) -> Dict[str, date]:
    """Get start and end dates of the month for given date"""
    if date_obj is None:
        date_obj = date.today()
    
    # First day of the month
    first_day = date_obj.replace(day=1)
    
    # Last day of the month
    if date_obj.month == 12:
        last_day = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)
    
    return {
        'start': first_day,
        'end': last_day
    }

def calculate_completion_rate(completed: int, total: int) -> float:
    """Calculate completion rate percentage"""
    if total == 0:
        return 0.0
    
    return (completed / total) * 100

def format_completion_rate(completed: int, total: int) -> str:
    """Format completion rate as string with percentage"""
    if total == 0:
        return "0% (0/0)"
    
    rate = (completed / total) * 100
    return f"{rate:.1f}% ({completed}/{total})"

def get_time_ago(datetime_obj: datetime) -> str:
    """Get human readable time ago string"""
    if datetime_obj is None:
        return "Unknown"
    
    now = datetime.now()
    
    if datetime_obj.date() == now.date():
        time_diff = now - datetime_obj
        
        if time_diff.seconds < 60:
            return "Just now"
        elif time_diff.seconds < 3600:
            minutes = time_diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            hours = time_diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days_diff = (now.date() - datetime_obj.date()).days
        
        if days_diff == 1:
            return "Yesterday"
        elif days_diff < 7:
            return f"{days_diff} days ago"
        elif days_diff < 30:
            weeks = days_diff // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            months = days_diff // 30
            return f"{months} month{'s' if months != 1 else ''} ago"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove extra spaces and dots
    filename = re.sub(r'\.+', '.', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "untitled"
    
    return filename

def format_machine_usage_time(start_time: datetime, end_time: datetime) -> str:
    """Format machine usage time duration"""
    if start_time is None or end_time is None:
        return "Unknown duration"
    
    duration = end_time - start_time
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def get_shift_from_time(time_obj: Union[datetime, str]) -> str:
    """Determine shift based on time"""
    if isinstance(time_obj, str):
        try:
            time_obj = datetime.strptime(time_obj, "%H:%M:%S").time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_obj, "%H:%M").time()
            except ValueError:
                return "Unknown"
    elif isinstance(time_obj, datetime):
        time_obj = time_obj.time()
    
    hour = time_obj.hour
    
    if 6 <= hour < 14:
        return "Morning"
    elif 14 <= hour < 22:
        return "Afternoon"
    else:
        return "Night"

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate that required fields are not empty"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field] or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)
    
    if missing_fields:
        st.error(f"The following required fields are missing: {', '.join(missing_fields)}")
        return False
    
    return True

def generate_summary_stats(data: List[Dict[str, Any]], numeric_fields: List[str]) -> Dict[str, Union[int, float]]:
    """Generate summary statistics for numeric fields in a dataset"""
    if not data:
        return {}
    
    stats = {}
    
    for field in numeric_fields:
        values = [item.get(field, 0) for item in data if item.get(field) is not None]
        
        if values:
            stats[f"{field}_total"] = sum(values)
            stats[f"{field}_average"] = sum(values) / len(values)
            stats[f"{field}_max"] = max(values)
            stats[f"{field}_min"] = min(values)
            stats[f"{field}_count"] = len(values)
        else:
            stats[f"{field}_total"] = 0
            stats[f"{field}_average"] = 0
            stats[f"{field}_max"] = 0
            stats[f"{field}_min"] = 0
            stats[f"{field}_count"] = 0
    
    return stats

def create_success_message(action: str, entity: str, entity_name: str = "") -> str:
    """Create standardized success message"""
    entity_display = f" '{entity_name}'" if entity_name else ""
    return f"{entity}{entity_display} {action} successfully!"

def create_error_message(action: str, entity: str, error_details: str = "") -> str:
    """Create standardized error message"""
    base_message = f"Error {action} {entity}"
    return f"{base_message}: {error_details}" if error_details else f"{base_message}"

def export_dataframe_to_csv(df: pd.DataFrame, filename: str) -> str:
    """Export dataframe to CSV and return the data"""
    return df.to_csv(index=False)
