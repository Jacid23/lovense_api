"""HTTP views for Lovense API integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web_request import Request

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LovenseCallbackView(HomeAssistantView):
    """Handle Lovense API callbacks."""

    url = "/api/lovense/callback"
    name = "api:lovense:callback"
    requires_auth = False  # Lovense will POST to this endpoint

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the callback view."""
        self.hass = hass

    async def post(self, request: Request) -> web.Response:
        """Handle POST requests from Lovense app."""
        try:
            # Parse the incoming data from Lovense Remote app
            data = await request.json()
            _LOGGER.info("Received Lovense callback: %s", data)
            
            # Extract user ID to find the right coordinator
            user_id = data.get("uid")
            if not user_id:
                _LOGGER.error("No user ID in callback data")
                return web.Response(text="Missing user ID", status=400)
            
            # Find the coordinator for this user
            coordinator = None
            for entry_id, coord in self.hass.data.get(DOMAIN, {}).items():
                if hasattr(coord, 'user_id') and coord.user_id == user_id:
                    coordinator = coord
                    break
            
            if not coordinator:
                _LOGGER.error("No coordinator found for user ID: %s", user_id)
                return web.Response(text="User not found", status=404)
            
            # Update coordinator with device info
            coordinator.update_device_info(data)
            
            # Parse and store toy information
            toys = data.get("toys", {})
            if toys:
                _LOGGER.info("Updated toy list: %s", list(toys.keys()))
            
            return web.Response(text="OK", status=200)
            
        except json.JSONDecodeError:
            _LOGGER.error("Invalid JSON in callback")
            return web.Response(text="Invalid JSON", status=400)
        except Exception as err:
            _LOGGER.exception("Error processing callback: %s", err)
            return web.Response(text="Internal error", status=500)


async def async_setup_views(hass: HomeAssistant) -> None:
    """Set up the HTTP views."""
    callback_view = LovenseCallbackView(hass)
    hass.http.register_view(callback_view)
    _LOGGER.info("Registered Lovense callback view at %s", callback_view.url)
