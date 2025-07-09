"""Services for Lovense API integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_PATTERN = "send_pattern"
SERVICE_SEND_COMMAND = "send_command"

SEND_PATTERN_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("pattern"): cv.string,
        vol.Optional("interval", default=1000): cv.positive_int,
        vol.Optional("duration", default=10): cv.positive_int,
    }
)

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("command"): cv.string,
        vol.Required("parameters"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Lovense API integration."""
    
    async def send_pattern_service(call: ServiceCall) -> None:
        """Handle send pattern service call."""
        entity_ids = call.data["entity_id"]
        pattern = call.data["pattern"]
        interval = call.data["interval"]
        duration = call.data["duration"]
        
        # Find coordinators for the entities
        coordinators = []
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            coordinators.append(coordinator)
        
        # Send pattern to all relevant devices
        for coordinator in coordinators:
            try:
                # Build pattern command
                rule = f"V:1;F:v;S:{interval}#"
                await coordinator.send_command_local(
                    command="Pattern",
                    rule=rule,
                    strength=pattern,
                    timeSec=duration,
                    apiVer=2,
                )
                _LOGGER.info("Sent pattern to coordinator: %s", pattern)
            except Exception as err:
                _LOGGER.error("Failed to send pattern: %s", err)

    async def send_command_service(call: ServiceCall) -> None:
        """Handle send command service call."""
        entity_ids = call.data["entity_id"]
        command = call.data["command"]
        parameters_str = call.data["parameters"]
        
        try:
            parameters = json.loads(parameters_str)
        except json.JSONDecodeError as err:
            _LOGGER.error("Invalid JSON in parameters: %s", err)
            return
        
        # Find coordinators for the entities
        coordinators = []
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            coordinators.append(coordinator)
        
        # Send command to all relevant devices
        for coordinator in coordinators:
            try:
                await coordinator.send_command_local(
                    command=command,
                    **parameters,
                )
                _LOGGER.info("Sent command %s to coordinator", command)
            except Exception as err:
                _LOGGER.error("Failed to send command %s: %s", command, err)
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_PATTERN,
        send_pattern_service,
        schema=SEND_PATTERN_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        send_command_service,
        schema=SEND_COMMAND_SCHEMA,
    )
    
    _LOGGER.info("Registered Lovense API services")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND_PATTERN)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
