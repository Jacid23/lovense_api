"""Constants for the Lovense API integration."""
from typing import Final

DOMAIN: Final = "lovense_api"

# Configuration keys
CONF_DEVELOPER_TOKEN: Final = "developer_token"
CONF_CALLBACK_URL: Final = "callback_url"
CONF_USER_ID: Final = "user_id"
CONF_USER_NAME: Final = "user_name"
CONF_STROKE_CONTROL_TYPE: Final = "stroke_control_type"

# API endpoints
API_BASE_URL: Final = "https://api.lovense-api.com/api"
API_GET_QRCODE: Final = f"{API_BASE_URL}/lan/getQrCode"
API_COMMAND_LOCAL: Final = "/command"  # Local endpoint, requires domain and port
API_COMMAND_SERVER: Final = f"{API_BASE_URL}/lan/v2/command"

# Device commands
CMD_GETTOYS: Final = "GetToys"
CMD_FUNCTION: Final = "Function"
CMD_POSITION: Final = "Position"
CMD_PATTERN: Final = "Pattern"
CMD_PRESET: Final = "Preset"

# Action types
ACTION_VIBRATE: Final = "Vibrate"
ACTION_ROTATE: Final = "Rotate"
ACTION_THRUSTING: Final = "Thrusting"
ACTION_STOP: Final = "Stop"

# Intensity ranges (based on official Lovense API)
VIBRATE_MIN: Final = 0
VIBRATE_MAX: Final = 20
POSITION_MIN: Final = 0
POSITION_MAX: Final = 100
TRAVEL_MIN: Final = 0
TRAVEL_MAX: Final = 100

# Update intervals
SCAN_INTERVAL: Final = 30  # seconds
REQUEST_TIMEOUT: Final = 10  # seconds

# Device types
SUPPORTED_DEVICES: Final = [
    "solace",
    "max",
    "nora",
    "lush",
    "domi",
    "edge",
    "lovense",
]

# Default API credentials (can be overridden in config)
DEFAULT_DEVELOPER_TOKEN: Final = "5tO8C-VU9F-G_wXXl6iyxqhEBZFFUbrm1MefQATfN0WdKiFkqjbJOV14k5OWm4H0"
DEFAULT_ENCRYPTION_KEY: Final = "3e7ea4eb38b197bc"
DEFAULT_ENCRYPTION_IV: Final = "967C5ABD66EBB2F8"

# Callback endpoint
CALLBACK_ENDPOINT: Final = "/api/lovense/callback"

# HTTP headers
DEFAULT_HEADERS: Final = {
    "Content-Type": "application/json",
    "User-Agent": "Home Assistant Lovense API Integration",
}

# QR code display settings
QR_CODE_EXPIRY: Final = 14400  # 4 hours in seconds
QR_CODE_SIZE: Final = 200  # pixels

# Error codes from Lovense API
ERROR_CODES: Final = {
    400: "Invalid Command",
    401: "Toy Not Found", 
    402: "Toy Not Connected",
    403: "Toy Doesn't Support This Command",
    404: "Invalid Parameter",
    500: "HTTP Server Not Started or Disabled",
    501: "Invalid Token",
    502: "No Permission to Use This API",
    503: "Invalid User ID",
    506: "Server Error - Restart Lovense Connect",
    507: "Lovense APP is Offline",
}

# Stroke control options
STROKE_CONTROL_LIGHTS: Final = "lights"  # Voice-friendly light entities
STROKE_CONTROL_NUMBERS: Final = "numbers"  # Precise number entities
STROKE_CONTROL_BOTH: Final = "both"  # Both types (for advanced users)
