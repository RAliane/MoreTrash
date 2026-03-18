"""
Utility helper functions for the FastAPI XGBoost Optimizer.

This module provides common utility functions for data transformation,
formatting, and other helper operations.
"""

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique identifier.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        str: Unique identifier
    """
    unique_id = str(uuid4())
    return f"{prefix}{unique_id}" if prefix else unique_id


def generate_deterministic_id(data: Dict[str, Any], prefix: str = "") -> str:
    """
    Generate a deterministic ID from data.
    
    Args:
        data: Input data
        prefix: Optional prefix for the ID
        
    Returns:
        str: Deterministic identifier
    """
    # Sort keys for consistent hashing
    sorted_data = json.dumps(data, sort_keys=True)
    
    # Generate hash
    data_hash = hashlib.sha256(sorted_data.encode()).hexdigest()
    
    # Return first 16 characters of hash
    id_hash = data_hash[:16]
    return f"{prefix}{id_hash}" if prefix else id_hash


def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize a string for safe use.
    
    Args:
        input_string: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized string
    """
    if not input_string:
        return ""
    
    # Remove control characters and extra whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_string)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length - 3] + "..."
    
    return sanitized


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid URL format
    """
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human readable string.
    
    Args:
        bytes_value: Bytes value
        
    Returns:
        str: Formatted string
    """
    if bytes_value == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(bytes_value)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """
    Format duration into human readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} min"
    else:
        hours = seconds / 3600
        return f"{hours:.2f} h"


def parse_boolean(value: Union[str, bool, int]) -> bool:
    """
    Parse a value as boolean.
    
    Args:
        value: Value to parse
        
    Returns:
        bool: Parsed boolean value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, int):
        return bool(value)
    
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    
    return False


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Dict[str, Any]: Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get a nested value from a dictionary using dot notation.
    
    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        
    Returns:
        Any: Value at path or default
    """
    keys = path.split(".")
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a nested value in a dictionary using dot notation.
    
    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "user.profile.name")
        value: Value to set
    """
    keys = path.split(".")
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def flatten_dict(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        data: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Dict[str, Any]: Flattened dictionary
    """
    items = []
    
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    """
    Unflatten a dictionary with dot notation keys.
    
    Args:
        data: Flattened dictionary
        sep: Separator used in keys
        
    Returns:
        Dict[str, Any]: Nested dictionary
    """
    result = {}
    
    for key, value in data.items():
        set_nested_value(result, key, value)
    
    return result


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely load JSON string with fallback.
    
    Args:
        json_string: JSON string to load
        default: Default value if parsing fails
        
    Returns:
        Any: Parsed JSON or default
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "") -> str:
    """
    Safely dump data to JSON string with fallback.
    
    Args:
        data: Data to dump
        default: Default value if dumping fails
        
    Returns:
        str: JSON string or default
    """
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


def truncate_string(input_string: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length.
    
    Args:
        input_string: String to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating
        
    Returns:
        str: Truncated string
    """
    if len(input_string) <= max_length:
        return input_string
    
    return input_string[:max_length - len(suffix)] + suffix


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from a dictionary.
    
    Args:
        data: Dictionary to clean
        
    Returns:
        Dict[str, Any]: Dictionary without None values
    """
    return {k: v for k, v in data.items() if v is not None}


def chunk_list(input_list: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        input_list: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List[List[Any]]: List of chunks
    """
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def find_duplicates(input_list: List[Any]) -> List[Any]:
    """
    Find duplicate values in a list.
    
    Args:
        input_list: List to check
        
    Returns:
        List[Any]: List of duplicate values
    """
    seen = set()
    duplicates = set()
    
    for item in input_list:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    
    return list(duplicates)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers with fallback.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        float: Division result or default
    """
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return default


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate percentile of a list of values.
    
    Args:
        values: List of values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        float: Percentile value
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = (percentile / 100) * (len(sorted_values) - 1)
    
    if index.is_integer():
        return sorted_values[int(index)]
    else:
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))


def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize a value to 0-1 range.
    
    Args:
        value: Value to normalize
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        float: Normalized value
    """
    if max_val == min_val:
        return 0.0
    
    return (value - min_val) / (max_val - min_val)


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between minimum and maximum.
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        float: Clamped value
    """
    return max(min_val, min(max_val, value))


def is_numeric(value: Any) -> bool:
    """
    Check if a value is numeric.
    
    Args:
        value: Value to check
        
    Returns:
        bool: True if numeric
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def convert_to_numeric(value: Any, default: float = 0.0) -> float:
    """
    Convert a value to numeric with fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        float: Numeric value or default
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Filename to extract extension from
        
    Returns:
        str: File extension (including dot)
    """
    return filename[filename.rfind('.'):] if '.' in filename else ""


def get_file_name_without_extension(filename: str) -> str:
    """
    Get filename without extension.
    
    Args:
        filename: Filename to process
        
    Returns:
        str: Filename without extension
    """
    return filename[:filename.rfind('.')] if '.' in filename else filename


def format_file_size(bytes_value: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        bytes_value: File size in bytes
        
    Returns:
        str: Formatted file size
    """
    return format_bytes(bytes_value)


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        uuid_string: String to check
        
    Returns:
        bool: True if valid UUID
    """
    try:
        from uuid import UUID
        UUID(uuid_string)
        return True
    except ValueError:
        return False


def get_environment_info() -> Dict[str, Any]:
    """
    Get environment information.
    
    Returns:
        Dict[str, Any]: Environment information
    """
    import sys
    import os
    
    return {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": sys.platform,
        "environment_variables": dict(os.environ),
        "working_directory": os.getcwd(),
        "timestamp": time.time(),
    }


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage information.
    
    Returns:
        Dict[str, float]: Memory usage information
    """
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
        }
        
    except ImportError:
        return {}


def get_cpu_usage() -> Dict[str, float]:
    """
    Get current CPU usage information.
    
    Returns:
        Dict[str, float]: CPU usage information
    """
    try:
        import psutil
        
        return {
            "percent": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count(),
        }
        
    except ImportError:
        return {}


def benchmark_function(func, *args, **kwargs) -> Dict[str, float]:
    """
    Benchmark a function execution.
    
    Args:
        func: Function to benchmark
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Dict[str, float]: Benchmark results
    """
    start_time = time.time()
    
    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as exc:
        result = None
        success = False
        error = str(exc)
    
    end_time = time.time()
    
    return {
        "execution_time": end_time - start_time,
        "success": success,
        "error": error,
        "result": result,
    }