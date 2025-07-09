"""Utility functions for Lovense API integration."""
from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urljoin

from .const import (
    DEFAULT_DEVELOPER_TOKEN,
    DEFAULT_ENCRYPTION_KEY,
    DEFAULT_ENCRYPTION_IV,
    ERROR_CODES,
)

_LOGGER = logging.getLogger(__name__)


def get_error_message(error_code: int) -> str:
    """Get human-readable error message from Lovense API error code."""
    return ERROR_CODES.get(error_code, f"Unknown error code: {error_code}")


def generate_device_id(device_info: dict[str, Any]) -> str:
    """Generate a stable device ID from device information."""
    # Use device ID if available
    if device_id := device_info.get("id"):
        return device_id
    
    # Use device name + type as fallback
    name = device_info.get("name", "unknown")
    toy_type = device_info.get("toyType", "device")
    
    # Create hash for consistent ID
    device_string = f"{name}_{toy_type}"
    device_hash = hashlib.md5(device_string.encode()).hexdigest()[:8]
    
    return f"{name.lower()}_{device_hash}"


def build_local_url(domain: str, port: int, endpoint: str = "/command") -> str:
    """Build local API URL for device communication."""
    base_url = f"https://{domain}:{port}"
    return urljoin(base_url, endpoint)


def validate_intensity(value: int, min_val: int, max_val: int) -> int:
    """Validate and clamp intensity value to valid range."""
    return max(min_val, min(max_val, int(value)))


def parse_toy_functions(toy_info: dict[str, Any]) -> list[str]:
    """Parse available functions from toy information."""
    functions = []
    
    # Get short function names (v, r, p, etc.)
    short_names = toy_info.get("shortFunctionNames", [])
    
    # Get full function names  
    full_names = toy_info.get("fullFunctionNames", [])
    
    # Map short names to standard actions
    function_map = {
        "v": "Vibrate",
        "r": "Rotate", 
        "p": "Pump",
        "t": "Thrusting",
        "f": "Fingering",
        "s": "Suction",
        "d": "Depth",
        "o": "Oscillate",
    }
    
    # Convert short names
    for short_name in short_names:
        if short_name in function_map:
            functions.append(function_map[short_name])
    
    # Add full names
    functions.extend(full_names)
    
    # Remove duplicates and return
    return list(set(functions))


def supports_position_control(toy_info: dict[str, Any]) -> bool:
    """Check if device supports position control (like Solace Pro)."""
    toy_type = toy_info.get("toyType", "").lower()
    toy_name = toy_info.get("name", "").lower()
    
    # Check for Solace Pro specifically
    if "solace" in toy_type or "solace" in toy_name:
        return True
    
    # Check for position-related functions
    functions = parse_toy_functions(toy_info)
    position_keywords = ["position", "stroke", "linear", "depth"]
    
    return any(
        keyword in " ".join(functions).lower() 
        for keyword in position_keywords
    )


def format_device_name(toy_info: dict[str, Any]) -> str:
    """Format a user-friendly device name."""
    name = toy_info.get("name", "Lovense Device")
    nickname = toy_info.get("nickName", "")
    
    if nickname and nickname != name:
        return f"{name} ({nickname})"
    
    return name


def get_api_credentials(config: dict[str, Any]) -> dict[str, str]:
    """Get API credentials from config with fallbacks."""
    return {
        "token": config.get("developer_token", DEFAULT_DEVELOPER_TOKEN),
        "key": config.get("encryption_key", DEFAULT_ENCRYPTION_KEY), 
        "iv": config.get("encryption_iv", DEFAULT_ENCRYPTION_IV),
    }


def is_device_connected(toy_info: dict[str, Any]) -> bool:
    """Check if device is currently connected."""
    # Check status field
    status = toy_info.get("status")
    if status is not None:
        return str(status) == "1"
    
    # Check connected field
    connected = toy_info.get("connected")
    if connected is not None:
        return bool(connected)
    
    # Default to unknown/disconnected
    return False


def get_battery_level(toy_info: dict[str, Any]) -> int | None:
    """Get battery level from toy info."""
    battery = toy_info.get("battery")
    if battery is not None:
        return max(0, min(100, int(battery)))
    
    return None


def get_device_version(toy_info: dict[str, Any]) -> str | None:
    """Get device firmware version."""
    # Try firmware version first
    if fversion := toy_info.get("fVersion"):
        return str(fversion)
    
    # Try hardware version
    if hversion := toy_info.get("hVersion"):
        return f"HW {hversion}"
    
    return None
