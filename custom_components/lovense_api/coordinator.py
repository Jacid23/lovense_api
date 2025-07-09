"""Data coordinator for Lovense API integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_GET_QRCODE,
    CMD_FUNCTION,
    CMD_POSITION,
    CONF_CALLBACK_URL,
    CONF_DEVELOPER_TOKEN,
    CONF_USER_ID,
    CONF_USER_NAME,
    DOMAIN,
    SCAN_INTERVAL,
    REQUEST_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class LovenseCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Lovense API."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        config: dict[str, Any],
    ) -> None:
        """Initialize."""
        self.session = session
        self.developer_token = config[CONF_DEVELOPER_TOKEN]
        self.callback_url = config[CONF_CALLBACK_URL]
        self.user_id = config[CONF_USER_ID]
        self.user_name = config.get(CONF_USER_NAME, "")
        
        # Device connection info (populated after QR code scan)
        self.device_info: dict[str, Any] = {}
        self.toy_data: dict[str, Any] = {}
        self.toys: dict[str, Any] = {}
        
        # Stroke position storage for each toy
        self.stroke_positions: dict[str, dict[str, int]] = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # If we don't have device info yet, try to get QR code for pairing
            if not self.device_info:
                await self._get_qr_code()
                return {"status": "awaiting_pairing", "toys": {}}
            
            # If we have device info, try to get toys
            toys = await self._get_toys()
            return {"status": "connected", "toys": toys}
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _get_qr_code(self) -> dict[str, Any]:
        """Get QR code for device pairing."""
        payload = {
            "token": self.developer_token,
            "uid": self.user_id,
            "uname": self.user_name,
            "v": 2,
        }
        
        try:
            async with self.session.post(
                API_GET_QRCODE,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("code") == 0:
                    _LOGGER.info("QR code generated successfully")
                    return data.get("data", {})
                else:
                    _LOGGER.error("Failed to get QR code: %s", data.get("message"))
                    raise UpdateFailed(f"API error: {data.get('message')}")
                    
        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error getting QR code: %s", err)
            raise UpdateFailed(f"HTTP error: {err}") from err

    async def _get_toys(self) -> dict[str, Any]:
        """Get connected toys information."""
        if not self.device_info:
            return {}
        
        # If we have toy data from callback, use that
        if hasattr(self, 'toy_data') and self.toy_data:
            return self.toy_data
            
        # Otherwise try to fetch from local API
        domain = self.device_info.get("domain")
        https_port = self.device_info.get("httpsPort")
        
        if domain and https_port:
            return await self._get_toys_local(domain, https_port)
        else:
            return await self._get_toys_server()

    async def _get_toys_local(self, domain: str, https_port: int) -> dict[str, Any]:
        """Get toys via local API."""
        url = f"https://{domain}:{https_port}/command"
        payload = {"command": "GetToys"}
        headers = {"X-platform": "Home Assistant Lovense Integration"}
        
        try:
            async with self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ssl=False,  # Lovense uses self-signed certificates
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("code") == 200:
                    return data.get("data", {})
                else:
                    _LOGGER.error("Local API error: %s", data)
                    return {}
                    
        except aiohttp.ClientError as err:
            _LOGGER.warning("Local API unavailable, using server API: %s", err)
            return await self._get_toys_server()

    async def _get_toys_server(self) -> dict[str, Any]:
        """Get toys via server API (fallback)."""
        # Server API would require different implementation
        # For now, return empty dict
        _LOGGER.info("Server API not yet implemented")
        return {}

    async def send_command_local(
        self,
        command: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send command to device via local API."""
        if not self.device_info:
            raise UpdateFailed("No device connection")
            
        domain = self.device_info.get("domain")
        https_port = self.device_info.get("httpsPort")
        
        if not (domain and https_port):
            raise UpdateFailed("No local connection available")
            
        url = f"https://{domain}:{https_port}/command"
        payload = {"command": command, "apiVer": 1, **kwargs}
        headers = {"X-platform": "Home Assistant Lovense Integration"}
        
        try:
            async with self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ssl=False,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("code") == 200:
                    return data
                else:
                    _LOGGER.error("Command failed: %s", data)
                    raise UpdateFailed(f"Command failed: {data}")
                    
        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error sending command: %s", err)
            raise UpdateFailed(f"HTTP error: {err}") from err

    def update_device_info(self, device_info: dict[str, Any]) -> None:
        """Update device info from callback."""
        old_toys = set(self.data.get("toys", {}).keys()) if self.data else set()
        self.device_info = device_info
        
        # Store toy data from callback
        self.toy_data = device_info.get("toys", {})
        _LOGGER.info("Device info updated: %s", device_info.get("domain"))
        
        # Check for new toys in the callback
        new_toys = set(self.toy_data.keys())
        if new_toys - old_toys:
            _LOGGER.info("New toys detected: %s", new_toys - old_toys)
            # Trigger platform reload for new entities
            self._trigger_platform_reload()
        
        # Trigger immediate data refresh
        asyncio.create_task(self.async_refresh())
    
    def _trigger_platform_reload(self) -> None:
        """Trigger platform reload to create entities for new devices."""
        # Find the config entry for this coordinator
        entry_id = None
        for eid, coordinator in self.hass.data.get(DOMAIN, {}).items():
            if coordinator == self:
                entry_id = eid
                break
        
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                # Schedule platform reload
                self.hass.async_create_task(self._reload_platforms(entry))
                _LOGGER.info("Triggered platform reload for new toys")
            else:
                _LOGGER.error("Could not find config entry for reload")
        else:
            _LOGGER.error("Could not find coordinator entry_id for reload")
    
    async def _reload_platforms(self, entry) -> None:
        """Reload platforms to create new entities."""
        try:
            # Instead of forward_entry_setups (which fails if already setup),
            # use async_request_refresh to trigger entity updates
            await self.async_request_refresh()
            self.async_update_listeners()
            _LOGGER.info("✅ Platforms refreshed - entities should appear now")
        except Exception as err:
            _LOGGER.error("❌ Failed to refresh platforms: %s", err)

    async def send_unified_command(self, toy_id: str, **settings) -> None:
        """Send a unified command that preserves all current settings."""
        # Initialize toy settings if not exists
        if not hasattr(self, 'toy_settings'):
            self.toy_settings = {}
        if toy_id not in self.toy_settings:
            self.toy_settings[toy_id] = {
                'vibration': 0,
                'position': None,
                'stroke_range': None,
                'thrusting': 0
            }
        
        # Update with new settings
        for key, value in settings.items():
            if key == 'stroke_range' and value is None:
                # Clear stroke range when explicitly set to None
                self.toy_settings[toy_id][key] = None
            elif value is not None:
                self.toy_settings[toy_id][key] = value
        
        current = self.toy_settings[toy_id]
        
        # Determine which command to use based on what's active
        if current['position'] is not None:
            # Use direct position control
            await self.send_command_local(
                command=CMD_POSITION,
                value=str(int(current['position'])),
                toy=toy_id,
            )
        elif current['vibration'] > 0 or current['stroke_range'] is not None or current['thrusting'] > 0:
            # Use function command with combined actions
            actions = []
            
            if current['vibration'] > 0:
                actions.append(f"Vibrate:{current['vibration']}")
            
            if current['stroke_range'] is not None:
                actions.append(f"Stroke:{current['stroke_range']}")
            
            if current['thrusting'] > 0:
                actions.append(f"Thrusting:{current['thrusting']}")
            
            if actions:
                action_string = ",".join(actions)
                await self.send_command_local(
                    command=CMD_FUNCTION,
                    action=action_string,
                    timeSec=0,
                    toy=toy_id,
                )
        else:
            # Stop all activity
            await self.send_command_local(
                command=CMD_FUNCTION,
                action="Stop",
                timeSec=0,
                toy=toy_id,
            )
