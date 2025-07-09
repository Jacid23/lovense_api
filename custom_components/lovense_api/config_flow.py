"""Config flow for Lovense API integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CALLBACK_URL,
    CONF_DEVELOPER_TOKEN,
    CONF_USER_ID,
    CONF_USER_NAME,
    DEFAULT_DEVELOPER_TOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEVELOPER_TOKEN, default=DEFAULT_DEVELOPER_TOKEN): str,
        vol.Required(CONF_CALLBACK_URL): str,
        vol.Required(CONF_USER_ID): str,
        vol.Optional(CONF_USER_NAME, default=""): str,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.
    
    TODO: Replace with actual implementation.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO: validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = PlaceholderHub(data["developer_token"])

    if not await hub.authenticate(data["user_id"], data["developer_token"]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": f"Lovense API ({data['user_id']})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lovense API."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Security validation for callback URL
            callback_url = user_input.get("callback_url", "")
            if callback_url:
                if not callback_url.startswith("https://"):
                    errors["callback_url"] = "callback_url_not_https"
                elif "localhost" in callback_url or "127.0.0.1" in callback_url:
                    errors["callback_url"] = "callback_url_localhost"
                elif ":8123" in callback_url and not any(safe in callback_url for safe in ["trycloudflare.com", "nabu.casa", "tailscale"]):
                    errors["callback_url"] = "callback_url_unsafe"
            
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "security_warning": "⚠️ NEVER expose Home Assistant directly to the internet! Use Cloudflare Tunnel, Nabu Casa, or Tailscale for secure callback URLs."
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
